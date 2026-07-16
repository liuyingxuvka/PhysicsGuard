"""Command line interface for PhysicsGuard Core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import yaml

from physicsguard.core.contract_diff import diff_test_file_contracts
from physicsguard.core.data_file_manifest import generate_delimited_manifest, manifest_to_dict
from physicsguard.core.dataset_identity import (
    check_logical_dataset_record,
    check_test_file_relation_index,
)
from physicsguard.core.evidence_mesh import check_evidence_mesh
from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.evaluator import AuditEvaluator
from physicsguard.core.hierarchy import HierarchicalAuditRunner, inspect_hierarchy, plan_from_report
from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.model_library import check_model_library_index
from physicsguard.core.project_closure import run_project_closure
from physicsguard.core.project_evidence import (
    build_project_evidence_map,
    check_evidence_bundle,
    check_evidence_gaps,
    check_project_evidence_registry,
    scan_project_evidence_candidates,
)
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.core.test_file_contract import (
    check_test_file_contract,
    check_test_file_parameter_coverage,
    check_test_file_project_index,
    inspect_test_file_contract,
)
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.io.test_file_contract_loader import load_yaml_mapping
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.schema.test_file_contract import ExtractorProfileSpec, TestBenchProfileSpec
from physicsguard.workflow import (
    adopt_project,
    audit_project,
    review_external_model_intake,
    review_model_understanding_preflight,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="physicsguard")
    subparsers = parser.add_subparsers(dest="command", required=True)
    solve_parser = subparsers.add_parser("solve", help="solve a PhysicsGuard YAML audit")
    solve_parser.add_argument("system", type=Path, help="path to a YAML SystemSpec")
    solve_parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    run_parser = subparsers.add_parser("run", help="alias for solve")
    run_parser.add_argument("system", type=Path, help="path to a YAML SystemSpec")
    run_parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="evaluate observed values without solving",
    )
    evaluate_parser.add_argument("system", type=Path, help="path to a YAML SystemSpec")
    evaluate_parser.add_argument(
        "observed",
        type=Path,
        help="path to a YAML ObservedValuesSpec",
    )
    evaluate_parser.add_argument(
        "--pretty",
        action="store_true",
        help="pretty-print JSON output",
    )

    compare_parser = subparsers.add_parser(
        "compare",
        help="solve a reference model and compare observed values",
    )
    compare_parser.add_argument("system", type=Path, help="path to a YAML SystemSpec")
    compare_parser.add_argument(
        "observed",
        type=Path,
        help="path to a YAML ObservedValuesSpec",
    )
    compare_parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    hierarchy_parser = subparsers.add_parser(
        "hierarchy",
        help="hierarchical coarse-to-fine audit commands",
    )
    hierarchy_subparsers = hierarchy_parser.add_subparsers(dest="hierarchy_command", required=True)

    hierarchy_run = hierarchy_subparsers.add_parser("run", help="run a hierarchical audit")
    hierarchy_run.add_argument("audit", type=Path, help="path to a YAML HierarchicalAuditSpec")
    hierarchy_run.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    hierarchy_inspect = hierarchy_subparsers.add_parser(
        "inspect",
        help="inspect a hierarchical audit without solving",
    )
    hierarchy_inspect.add_argument("audit", type=Path, help="path to a YAML HierarchicalAuditSpec")
    hierarchy_inspect.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    hierarchy_plan = hierarchy_subparsers.add_parser(
        "plan",
        help="run a hierarchical audit and print only refinement planning data",
    )
    hierarchy_plan.add_argument("audit", type=Path, help="path to a YAML HierarchicalAuditSpec")
    hierarchy_plan.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    hierarchy_evaluate = hierarchy_subparsers.add_parser(
        "evaluate",
        help="evaluate observed values with hierarchical block roll-up and no solve",
    )
    hierarchy_evaluate.add_argument("audit", type=Path, help="path to a YAML HierarchicalAuditSpec")
    hierarchy_evaluate.add_argument(
        "observed",
        type=Path,
        help="path to a YAML ObservedValuesSpec",
    )
    hierarchy_evaluate.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    hierarchy_compare = hierarchy_subparsers.add_parser(
        "compare",
        help="solve a reference hierarchy and compare observed values",
    )
    hierarchy_compare.add_argument("audit", type=Path, help="path to a YAML HierarchicalAuditSpec")
    hierarchy_compare.add_argument(
        "observed",
        type=Path,
        help="path to a YAML ObservedValuesSpec",
    )
    hierarchy_compare.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    assumptions_parser = subparsers.add_parser(
        "assumptions",
        help="assumption card commands",
    )
    assumptions_subparsers = assumptions_parser.add_subparsers(dest="assumptions_command", required=True)
    assumptions_inspect = assumptions_subparsers.add_parser(
        "inspect",
        help="inspect assumption cards without solving",
    )
    assumptions_inspect.add_argument("system", type=Path, help="path to a YAML SystemSpec")
    assumptions_inspect.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    project_parser = subparsers.add_parser(
        "project",
        help="PhysicsGuard project adoption commands",
    )
    project_subparsers = project_parser.add_subparsers(dest="project_command", required=True)
    for command_name in ("adopt", "audit", "upgrade"):
        command_parser = project_subparsers.add_parser(
            command_name,
            help=f"{command_name} PhysicsGuard workflow adoption records",
        )
        command_parser.add_argument("--root", type=Path, default=Path("."), help="project root")
        command_parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    project_closure = project_subparsers.add_parser(
        "closure",
        help="run project-level closure readiness checks",
    )
    project_closure.add_argument("plan", type=Path, help="path to ProjectClosurePlan YAML")
    project_closure.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    preflight_parser = subparsers.add_parser(
        "preflight",
        help="model-understanding preflight commands",
    )
    preflight_subparsers = preflight_parser.add_subparsers(dest="preflight_command", required=True)
    preflight_review = preflight_subparsers.add_parser(
        "review",
        help="review a PhysicsGuard model-understanding preflight YAML",
    )
    preflight_review.add_argument("preflight", type=Path, help="path to preflight YAML")
    preflight_review.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    intake_parser = subparsers.add_parser(
        "intake",
        help="external model intake commands",
    )
    intake_subparsers = intake_parser.add_subparsers(dest="intake_command", required=True)
    intake_review = intake_subparsers.add_parser(
        "review",
        help="review a PhysicsGuard external-model intake YAML",
    )
    intake_review.add_argument("intake", type=Path, help="path to intake YAML")
    intake_review.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    testfile_parser = subparsers.add_parser(
        "testfile",
        help="testbench data-file contract commands",
    )
    testfile_subparsers = testfile_parser.add_subparsers(dest="testfile_command", required=True)
    testfile_manifest = testfile_subparsers.add_parser(
        "manifest",
        help="generate a manifest from a CSV/TSV test data file",
    )
    testfile_manifest.add_argument("data_file", type=Path, help="path to CSV/TSV test data file")
    testfile_manifest.add_argument("--profile", type=Path, help="testbench or extractor profile YAML")
    testfile_manifest.add_argument("--out", type=Path, help="write manifest YAML to this path")
    testfile_manifest.add_argument("--delimiter", help="CSV delimiter override")
    testfile_manifest.add_argument("--encoding", help="file encoding override")
    testfile_manifest.add_argument("--time-column", help="time column override")
    testfile_manifest.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    testfile_inspect = testfile_subparsers.add_parser(
        "inspect",
        help="inspect a resolved test-file contract",
    )
    testfile_inspect.add_argument("contract", type=Path, help="path to TestFileContract YAML")
    testfile_inspect.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    testfile_contract_check = testfile_subparsers.add_parser(
        "contract-check",
        help="check a test-file contract",
    )
    testfile_contract_check.add_argument("contract", type=Path, help="path to TestFileContract YAML")
    testfile_contract_check.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    testfile_project_check = testfile_subparsers.add_parser(
        "project-check",
        help="check all test-file contracts referenced by a project index",
    )
    testfile_project_check.add_argument("index", type=Path, help="path to TestFileProjectIndex YAML")
    testfile_project_check.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    testfile_diff = testfile_subparsers.add_parser(
        "diff",
        help="diff two resolved test-file contracts",
    )
    testfile_diff.add_argument("old_contract", type=Path, help="old TestFileContract YAML")
    testfile_diff.add_argument("new_contract", type=Path, help="new TestFileContract YAML")
    testfile_diff.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    coverage_parser = subparsers.add_parser(
        "coverage",
        help="parameter coverage contract commands",
    )
    coverage_subparsers = coverage_parser.add_subparsers(dest="coverage_command", required=True)
    coverage_check_parser = coverage_subparsers.add_parser(
        "check",
        help="check parameter coverage for a test-file contract",
    )
    coverage_check_parser.add_argument("contract", type=Path, help="path to TestFileContract YAML")
    coverage_check_parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    dataset_parser = subparsers.add_parser(
        "dataset",
        help="logical test dataset identity commands",
    )
    dataset_subparsers = dataset_parser.add_subparsers(dest="dataset_command", required=True)
    dataset_logical_check = dataset_subparsers.add_parser(
        "logical-check",
        help="check a logical dataset record",
    )
    dataset_logical_check.add_argument("record", type=Path, help="path to LogicalDatasetRecord YAML")
    dataset_logical_check.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    dataset_relation_check = dataset_subparsers.add_parser(
        "relation-check",
        help="check a test-file relation index",
    )
    dataset_relation_check.add_argument("index", type=Path, help="path to TestFileRelationIndex YAML")
    dataset_relation_check.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    validation_parser = subparsers.add_parser(
        "validation",
        help="model-dataset validation commands",
    )
    validation_subparsers = validation_parser.add_subparsers(dest="validation_command", required=True)
    validation_run = validation_subparsers.add_parser(
        "run",
        help="run a model-dataset validation plan",
    )
    validation_run.add_argument("plan", type=Path, help="path to ModelValidationPlan YAML")
    validation_run.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    validation_receipt = validation_subparsers.add_parser(
        "receipt",
        help="emit the native validation-depth receipt for a validation plan",
    )
    validation_receipt.add_argument("plan", type=Path, help="path to ModelValidationPlan YAML")
    validation_receipt.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    model_library_parser = subparsers.add_parser(
        "model-library",
        help="model library index commands",
    )
    model_library_subparsers = model_library_parser.add_subparsers(
        dest="model_library_command",
        required=True,
    )
    model_library_check = model_library_subparsers.add_parser(
        "check",
        help="check a model library index",
    )
    model_library_check.add_argument("index", type=Path, help="path to ModelLibraryIndex YAML")
    model_library_check.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

    evidence_parser = subparsers.add_parser(
        "evidence",
        help="project evidence registry commands",
    )
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_check = evidence_subparsers.add_parser(
        "check",
        help="check a project evidence registry",
    )
    evidence_check.add_argument("registry", type=Path, help="path to ProjectEvidenceRegistry YAML")
    evidence_check.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    evidence_scan = evidence_subparsers.add_parser(
        "scan",
        help="scan a project tree for candidate evidence artifacts",
    )
    evidence_scan.add_argument("root", type=Path, help="project root or folder to scan")
    evidence_scan.add_argument("--registry", type=Path, help="optional ProjectEvidenceRegistry YAML")
    evidence_scan.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    evidence_gap = evidence_subparsers.add_parser(
        "gap-check",
        help="check required evidence gaps",
    )
    evidence_gap.add_argument("registry", type=Path, help="path to ProjectEvidenceRegistry YAML")
    evidence_gap.add_argument("--bundle-id", help="optional evidence bundle id to check")
    evidence_gap.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    evidence_bundle = evidence_subparsers.add_parser(
        "bundle-check",
        help="check one evidence bundle for blocking gaps",
    )
    evidence_bundle.add_argument("registry", type=Path, help="path to ProjectEvidenceRegistry YAML")
    evidence_bundle.add_argument("bundle_id", help="evidence bundle id")
    evidence_bundle.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    evidence_map = evidence_subparsers.add_parser(
        "map",
        help="build an AI-readable project evidence map",
    )
    evidence_map.add_argument("registry", type=Path, help="path to ProjectEvidenceRegistry YAML")
    evidence_map.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    evidence_mesh = evidence_subparsers.add_parser(
        "mesh-check",
        help="check a FlowGuard-grade evidence mesh",
    )
    evidence_mesh.add_argument("mesh", type=Path, help="path to EvidenceMesh YAML")
    evidence_mesh.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    return parser


def _print_json(output: dict, pretty: bool) -> None:
    if pretty:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(json.dumps(output, sort_keys=True))


def solve(path: Path, pretty: bool = False) -> int:
    system = load_system_spec(path)
    builder = ResidualBuilder(system)
    solver = BoundedSolver(builder, system.solver)
    solver_result = solver.solve()
    reporter = DiagnosticReporter()
    report = reporter.generate(system, builder, solver_result)
    _print_json(reporter.to_dict(report), pretty)
    return 0


def evaluate(system_path: Path, observed_path: Path, pretty: bool = False) -> int:
    system = load_system_spec(system_path)
    observed = load_observed_values(observed_path)
    report = AuditEvaluator(system).evaluate_observed(observed)
    _print_json(DiagnosticReporter().to_dict(report), pretty)
    return 0


def compare(system_path: Path, observed_path: Path, pretty: bool = False) -> int:
    system = load_system_spec(system_path)
    observed = load_observed_values(observed_path)
    report = AuditEvaluator(system).compare_to_reference(observed)
    _print_json(DiagnosticReporter().to_dict(report), pretty)
    return 0


def hierarchy_run(path: Path, pretty: bool = False) -> int:
    spec = load_hierarchical_audit_spec(path)
    runner = HierarchicalAuditRunner(spec)
    report = runner.run()
    _print_json(runner.to_dict(report), pretty)
    return 0


def hierarchy_inspect(path: Path, pretty: bool = False) -> int:
    spec = load_hierarchical_audit_spec(path)
    _print_json(inspect_hierarchy(spec), pretty)
    return 0


def hierarchy_plan(path: Path, pretty: bool = False) -> int:
    spec = load_hierarchical_audit_spec(path)
    runner = HierarchicalAuditRunner(spec)
    report = runner.run()
    _print_json(plan_from_report(report), pretty)
    return 0


def hierarchy_evaluate(path: Path, observed_path: Path, pretty: bool = False) -> int:
    spec = load_hierarchical_audit_spec(path)
    observed = load_observed_values(observed_path)
    runner = HierarchicalAuditRunner(spec)
    report = runner.evaluate_observed(observed)
    _print_json(runner.to_dict(report), pretty)
    return 0


def hierarchy_compare(path: Path, observed_path: Path, pretty: bool = False) -> int:
    spec = load_hierarchical_audit_spec(path)
    observed = load_observed_values(observed_path)
    runner = HierarchicalAuditRunner(spec)
    report = runner.compare_observed(observed)
    _print_json(runner.to_dict(report), pretty)
    return 0


def assumptions_inspect(path: Path, pretty: bool = False) -> int:
    system = load_system_spec(path)
    builder = ResidualBuilder(system)
    _print_json(DiagnosticReporter().to_dict(builder.assumption_summary()), pretty)
    return 0


def project_command(command: str, root: Path, pretty: bool = False) -> int:
    if command == "audit":
        output = audit_project(root)
    else:
        output = adopt_project(root, action=command)
    _print_json(output, pretty)
    return 0 if output.get("ok", output.get("status") in {"pass", "pass_with_gaps"}) else 1


def project_closure_command(path: Path, pretty: bool = False) -> int:
    report = run_project_closure(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def preflight_review(path: Path, pretty: bool = False) -> int:
    report = review_model_understanding_preflight(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def intake_review(path: Path, pretty: bool = False) -> int:
    report = review_external_model_intake(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def testfile_manifest_command(
    data_file: Path,
    *,
    profile_path: Path | None = None,
    out: Path | None = None,
    delimiter: str | None = None,
    encoding: str | None = None,
    time_column: str | None = None,
    pretty: bool = False,
) -> int:
    profile = _load_manifest_profile(profile_path) if profile_path is not None else None
    manifest = generate_delimited_manifest(
        data_file,
        profile=profile,
        delimiter=delimiter,
        encoding=encoding,
        time_column=time_column,
    )
    output = manifest_to_dict(manifest)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(output, sort_keys=False), encoding="utf-8")
    else:
        _print_json(output, pretty)
    return 0


def testfile_inspect_command(path: Path, pretty: bool = False) -> int:
    _print_json(inspect_test_file_contract(path), pretty)
    return 0


def testfile_contract_check_command(path: Path, pretty: bool = False) -> int:
    report = check_test_file_contract(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def testfile_project_check_command(path: Path, pretty: bool = False) -> int:
    report = check_test_file_project_index(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def testfile_diff_command(old_contract: Path, new_contract: Path, pretty: bool = False) -> int:
    report = diff_test_file_contracts(old_contract, new_contract)
    _print_json(report.to_dict(), pretty)
    return 0


def coverage_check_command(path: Path, pretty: bool = False) -> int:
    report = check_test_file_parameter_coverage(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def dataset_logical_check_command(path: Path, pretty: bool = False) -> int:
    report = check_logical_dataset_record(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def dataset_relation_check_command(path: Path, pretty: bool = False) -> int:
    report = check_test_file_relation_index(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def validation_run_command(path: Path, pretty: bool = False) -> int:
    report = validate_model_dataset(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def validation_receipt_command(path: Path, pretty: bool = False) -> int:
    report = validate_model_dataset(path)
    receipt = report.depth_receipt
    _print_json(receipt, pretty)
    return 0 if receipt.get("ok") is True else 1


def model_library_check_command(path: Path, pretty: bool = False) -> int:
    report = check_model_library_index(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def evidence_check_command(path: Path, pretty: bool = False) -> int:
    report = check_project_evidence_registry(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def evidence_scan_command(root: Path, registry: Path | None = None, pretty: bool = False) -> int:
    report = scan_project_evidence_candidates(root, registry)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def evidence_gap_check_command(path: Path, bundle_id: str | None = None, pretty: bool = False) -> int:
    report = check_evidence_gaps(path, bundle_id)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def evidence_bundle_check_command(path: Path, bundle_id: str, pretty: bool = False) -> int:
    report = check_evidence_bundle(path, bundle_id)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def evidence_map_command(path: Path, pretty: bool = False) -> int:
    report = build_project_evidence_map(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def evidence_mesh_check_command(path: Path, pretty: bool = False) -> int:
    report = check_evidence_mesh(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def _load_manifest_profile(path: Path) -> TestBenchProfileSpec | ExtractorProfileSpec:
    data = load_yaml_mapping(path)
    if "script" in data:
        return ExtractorProfileSpec.model_validate(data)
    return TestBenchProfileSpec.model_validate(data)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {"run", "solve"}:
            return solve(args.system, args.pretty)
        if args.command == "evaluate":
            return evaluate(args.system, args.observed, args.pretty)
        if args.command == "compare":
            return compare(args.system, args.observed, args.pretty)
        if args.command == "hierarchy":
            if args.hierarchy_command == "run":
                return hierarchy_run(args.audit, args.pretty)
            if args.hierarchy_command == "inspect":
                return hierarchy_inspect(args.audit, args.pretty)
            if args.hierarchy_command == "plan":
                return hierarchy_plan(args.audit, args.pretty)
            if args.hierarchy_command == "evaluate":
                return hierarchy_evaluate(args.audit, args.observed, args.pretty)
            if args.hierarchy_command == "compare":
                return hierarchy_compare(args.audit, args.observed, args.pretty)
        if args.command == "assumptions":
            if args.assumptions_command == "inspect":
                return assumptions_inspect(args.system, args.pretty)
        if args.command == "project":
            if args.project_command == "closure":
                return project_closure_command(args.plan, args.pretty)
            return project_command(args.project_command, args.root, args.pretty)
        if args.command == "preflight":
            if args.preflight_command == "review":
                return preflight_review(args.preflight, args.pretty)
        if args.command == "intake":
            if args.intake_command == "review":
                return intake_review(args.intake, args.pretty)
        if args.command == "testfile":
            if args.testfile_command == "manifest":
                return testfile_manifest_command(
                    args.data_file,
                    profile_path=args.profile,
                    out=args.out,
                    delimiter=args.delimiter,
                    encoding=args.encoding,
                    time_column=args.time_column,
                    pretty=args.pretty,
                )
            if args.testfile_command == "inspect":
                return testfile_inspect_command(args.contract, args.pretty)
            if args.testfile_command == "contract-check":
                return testfile_contract_check_command(args.contract, args.pretty)
            if args.testfile_command == "project-check":
                return testfile_project_check_command(args.index, args.pretty)
            if args.testfile_command == "diff":
                return testfile_diff_command(args.old_contract, args.new_contract, args.pretty)
        if args.command == "coverage":
            if args.coverage_command == "check":
                return coverage_check_command(args.contract, args.pretty)
        if args.command == "dataset":
            if args.dataset_command == "logical-check":
                return dataset_logical_check_command(args.record, args.pretty)
            if args.dataset_command == "relation-check":
                return dataset_relation_check_command(args.index, args.pretty)
        if args.command == "validation":
            if args.validation_command == "run":
                return validation_run_command(args.plan, args.pretty)
            if args.validation_command == "receipt":
                return validation_receipt_command(args.plan, args.pretty)
        if args.command == "model-library":
            if args.model_library_command == "check":
                return model_library_check_command(args.index, args.pretty)
        if args.command == "evidence":
            if args.evidence_command == "check":
                return evidence_check_command(args.registry, args.pretty)
            if args.evidence_command == "scan":
                return evidence_scan_command(args.root, args.registry, args.pretty)
            if args.evidence_command == "gap-check":
                return evidence_gap_check_command(args.registry, args.bundle_id, args.pretty)
            if args.evidence_command == "bundle-check":
                return evidence_bundle_check_command(args.registry, args.bundle_id, args.pretty)
            if args.evidence_command == "map":
                return evidence_map_command(args.registry, args.pretty)
            if args.evidence_command == "mesh-check":
                return evidence_mesh_check_command(args.mesh, args.pretty)
    except Exception as exc:
        print(f"physicsguard error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
