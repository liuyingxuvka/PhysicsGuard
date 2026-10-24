"""Command line interface for PhysicsGuard Core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="physicsguard")
    subparsers = parser.add_subparsers(dest="command", required=True)
    modules_parser = subparsers.add_parser("modules", help="list and describe registered native module types")
    module_commands = modules_parser.add_subparsers(dest="modules_command", required=True)
    module_commands.add_parser("list", help="list every module type and its purpose")
    module_describe = module_commands.add_parser("describe", help="describe a native module contract using marked synthetic inputs")
    module_describe.add_argument("module_type")
    module_describe.add_argument("--pretty", action="store_true")
    hierarchy_parser = subparsers.add_parser(
        "hierarchy",
        help="hierarchical coarse-to-fine audit commands",
    )
    hierarchy_subparsers = hierarchy_parser.add_subparsers(dest="hierarchy_command", required=True)
    hierarchy_description = hierarchy_subparsers.add_parser("describe", help="print a readable declared tree without solving")
    hierarchy_description.add_argument("audit", type=Path)
    description_format = hierarchy_description.add_mutually_exclusive_group()
    description_format.add_argument("--mermaid", action="store_true")
    description_format.add_argument("--json", action="store_true", help="print the full declared structure")
    hierarchy_description.add_argument("--observed", type=Path, help="count mapped snapshot signals without evaluation")
    hierarchy_description.add_argument("--pretty", action="store_true")

    hierarchy_run = hierarchy_subparsers.add_parser("run", help="run a hierarchical audit")
    hierarchy_run.add_argument("audit", type=Path, help="path to a YAML HierarchicalAuditSpec")
    hierarchy_run.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    hierarchy_run.add_argument("--json", action="store_true", help="print the full report instead of the summary")

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
    hierarchy_evaluate.add_argument("--json", action="store_true", help="print the full report instead of the summary")

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
    hierarchy_compare.add_argument("--json", action="store_true", help="print the full report instead of the summary")

    hierarchy_variants = hierarchy_subparsers.add_parser("variants", help="compare model-derived fault signatures and next signals")
    hierarchy_variants.add_argument("audit", type=Path)
    hierarchy_variants.add_argument("nominal", type=Path)
    hierarchy_variants.add_argument("--pairs", action="store_true")
    hierarchy_variants.add_argument("--observed", type=Path)
    hierarchy_variants.add_argument("--json", action="store_true", help="print full generated values and pairwise evidence")
    hierarchy_variants.add_argument("--pretty", action="store_true")

    assumptions_parser = subparsers.add_parser(
        "assumptions",
        help="assumption card commands",
    )
    assumptions_subparsers = assumptions_parser.add_subparsers(dest="assumptions_command", required=True)
    assumptions_inspect = assumptions_subparsers.add_parser(
        "inspect",
        help="inspect assumption cards without solving",
    )
    assumptions_inspect.add_argument("system", type=Path, help="path to a YAML SystemSpec or hierarchical audit")
    assumptions_inspect.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

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
    preflight_review.add_argument("--audit", type=Path, help="check declared blocks against this audit model")
    preflight_review.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

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

    for kind in ('snapshot', 'series'):
        command = testfile_subparsers.add_parser(kind, help='convert declared CSV/TSV fields into SI observations')
        command.add_argument('contract', type=Path)
        command.add_argument('--out', type=Path)
        command.add_argument('--pretty', action='store_true')
        if kind == 'snapshot':
            command.add_argument('--row', type=int, required=True, help='zero-based source row')
        else:
            command.add_argument('--rows', help='zero-based A:B, end exclusive; default all usable rows')

    testfile_diff = testfile_subparsers.add_parser(
        "diff",
        help="diff two resolved test-file contracts",
    )
    testfile_diff.add_argument("old_contract", type=Path, help="old TestFileContract YAML")
    testfile_diff.add_argument("new_contract", type=Path, help="new TestFileContract YAML")
    testfile_diff.add_argument("--pretty", action="store_true", help="pretty-print JSON output")

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
    validation_run.add_argument("--json", action="store_true", help="print the full report instead of the summary")

    return parser


def _print_json(output: dict, pretty: bool) -> None:
    if pretty:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(json.dumps(output, sort_keys=True))


SUMMARY_HINT = "summary only; add --json for the full report"


def _pick(row: dict, keys: tuple[str, ...]) -> dict:
    return {key: row.get(key) for key in keys}


def _print_tree(spec, base_dir: Path, report: dict | None = None, variants: dict | None = None) -> None:
    """Compose the read-only structure with a report or a variant result into one tree view."""
    from physicsguard.core.hierarchy import describe_hierarchy
    from physicsguard.core.tree_view import render_tree_view

    print(render_tree_view(describe_hierarchy(spec, base_dir=base_dir), report=report, variants=variants))


def _validation_summary(report: dict) -> dict:
    direct = report.get("direct_validation", {})
    calibration = report.get("calibration", {})
    return {
        "output": SUMMARY_HINT,
        "validation_id": report.get("validation_id"),
        "status": report.get("status"),
        "ok": report.get("ok"),
        "direct_validation": {
            "audit_pass": direct.get("audit_pass"),
            "max_abs_normalized_residual": direct.get("max_abs_normalized_residual"),
            "top_blocks": [block.get("block_id") for block in direct.get("top_blocks", [])[:5]],
        },
        "calibration": _pick(calibration, ("enabled", "optimization_success", "holdout_audit_pass", "parameters_at_bounds")),
        "depth_summary": report.get("depth_summary", {}),
        "findings": [_pick(item, ("severity", "type", "target", "message")) for item in report.get("findings", [])],
        "safe_claim": report.get("safe_claim"),
        "unsafe_claim_boundary": report.get("unsafe_claim_boundary"),
        "next_actions": report.get("next_actions", []),
    }


def hierarchy_run(path: Path, pretty: bool = False, full: bool = False) -> int:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    spec = load_hierarchical_audit_spec(path)
    runner = HierarchicalAuditRunner(spec, base_dir=path.parent)
    report = runner.to_dict(runner.run())
    if full:
        _print_json(report, pretty)
    else:
        _print_tree(spec, path.parent, report=report)
    return 0 if report["audit_pass"] else 1


def modules_command(module_type: str | None = None, pretty: bool = False) -> int:
    from physicsguard.modules.registry import default_module_registry, describe_module_type

    registry = default_module_registry()
    if module_type is None:
        for name in registry.registered_types():
            print(f"{name}: {registry.type_summary(name)}")
    else:
        _print_json(describe_module_type(module_type, registry), pretty)
    return 0


def hierarchy_describe(path: Path, mermaid: bool = False, pretty: bool = False,
                       full: bool = False, observed_path: Path | None = None) -> int:
    from physicsguard.core.hierarchy import describe_hierarchy
    from physicsguard.core.tree_view import render_tree_view
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    observed = load_observed_values(observed_path) if observed_path is not None else None
    description = describe_hierarchy(load_hierarchical_audit_spec(path), mermaid=mermaid,
                                     observed=observed, base_dir=path.parent)
    if mermaid:
        print(description)
    elif full:
        _print_json(description, pretty)
    else:
        print(render_tree_view(description))
    return 0


def hierarchy_evaluate(path: Path, observed_path: Path, pretty: bool = False, full: bool = False) -> int:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(path)
    observed = load_observed_values(observed_path)
    runner = HierarchicalAuditRunner(spec, base_dir=path.parent)
    report = runner.to_dict(runner.evaluate_observed(observed, skip_unobserved=True))
    if full:
        _print_json(report, pretty)
    else:
        _print_tree(spec, path.parent, report=report)
    return 0 if report["audit_pass"] else 1


def hierarchy_compare(path: Path, observed_path: Path, pretty: bool = False, full: bool = False) -> int:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(path)
    observed = load_observed_values(observed_path)
    runner = HierarchicalAuditRunner(spec, base_dir=path.parent)
    report = runner.to_dict(runner.compare_observed(observed))
    if full:
        _print_json(report, pretty)
    else:
        _print_tree(spec, path.parent, report=report)
    return 0 if report["observed_audit_pass"] else 1


def hierarchy_variants_command(audit, nominal, pairs=False, observed=None, full=False, pretty=False) -> int:
    from physicsguard.core.diagnosability import evaluate_fault_variants
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(audit)
    output = evaluate_fault_variants(
        spec, load_observed_values(nominal), pairs=pairs,
        observed=load_observed_values(observed) if observed is not None else None, base_dir=audit.parent,
    )
    if full:
        _print_json(output, pretty)
    else:
        _print_tree(spec, audit.parent, variants=output)
    return 0 if output["ok"] and output["model_miss"] is not True else 1


def assumptions_inspect(path: Path, pretty: bool = False) -> int:
    from physicsguard.core.diagnostics import DiagnosticReporter
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.test_file_contract_loader import load_yaml_mapping
    from physicsguard.io.yaml_loader import load_system_spec

    data = load_yaml_mapping(path)
    system = (
        load_hierarchical_audit_spec(path).system
        if "hierarchy" in data and "system" in data
        else load_system_spec(path)
    )
    builder = ResidualBuilder(system)
    _print_json(DiagnosticReporter().to_dict(builder.assumption_summary()), pretty)
    return 0


def preflight_review(path: Path, pretty: bool = False, audit: Path | None = None) -> int:
    from physicsguard.workflow import review_model_understanding_preflight

    report = review_model_understanding_preflight(path, audit=audit)
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
    import yaml
    from physicsguard.core.data_file_manifest import generate_delimited_manifest, manifest_to_dict

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
        import os

        try:
            output["source_file"]["path"] = Path(os.path.relpath(data_file.resolve(), out.parent.resolve())).as_posix()
        except ValueError:
            # Different Windows drives have no relative path.
            output["source_file"]["path"] = data_file.resolve().as_posix()
        script = Path(output['extractor']['script'])
        if script.is_file():
            try:
                output['extractor']['script'] = Path(os.path.relpath(script.resolve(), out.parent.resolve())).as_posix()
            except ValueError:
                output['extractor']['script'] = script.resolve().as_posix()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(output, sort_keys=False), encoding="utf-8")
    else:
        _print_json(output, pretty)
    return 0


def testfile_inspect_command(path: Path, pretty: bool = False) -> int:
    from physicsguard.core.test_file_contract import inspect_test_file_contract

    _print_json(inspect_test_file_contract(path), pretty)
    return 0


def testfile_contract_check_command(path: Path, pretty: bool = False) -> int:
    from physicsguard.core.test_file_contract import check_test_file_contract

    report = check_test_file_contract(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def testfile_diff_command(old_contract: Path, new_contract: Path, pretty: bool = False) -> int:
    from physicsguard.core.contract_diff import diff_test_file_contracts

    report = diff_test_file_contracts(old_contract, new_contract)
    _print_json(report.to_dict(), pretty)
    return 0


def validation_run_command(path: Path, pretty: bool = False, full: bool = False) -> int:
    from physicsguard.core.model_dataset_validation import validate_model_dataset

    report = validate_model_dataset(path)
    _print_json(report.to_dict() if full else _validation_summary(report.to_dict()), pretty)
    return 0 if report.ok else 1


def _load_manifest_profile(path):
    from physicsguard.io.test_file_contract_loader import load_yaml_mapping, load_test_file_contract
    from physicsguard.schema.test_file_contract import TestBenchProfileSpec, ExtractorProfileSpec
    data = load_yaml_mapping(path)
    if 'fields' in data and 'data_file' in data:
        contract = load_test_file_contract(path)
        common = dict(time_column=contract.time_column, field_units={name:f.unit for name,f in contract.fields.items() if f.unit})
        if contract.extractor:
            profile = contract.extractor.model_copy(update=common)
        else:
            return TestBenchProfileSpec(profile_id=contract.contract_id, **common)
    elif 'script' in data:
        profile = ExtractorProfileSpec.model_validate(data)
    else:
        return TestBenchProfileSpec.model_validate(data)
    script = path.resolve().parent / profile.script
    if script.is_file():
        profile = profile.model_copy(update={'script': str(script.resolve())})
    return profile


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "modules":
            return modules_command(args.module_type if args.modules_command == "describe" else None,
                                   getattr(args, "pretty", False))
        if args.command == "hierarchy":
            if args.hierarchy_command == "describe":
                return hierarchy_describe(args.audit, args.mermaid, args.pretty, args.json, args.observed)
            if args.hierarchy_command == "run":
                return hierarchy_run(args.audit, args.pretty, args.json)
            if args.hierarchy_command == "evaluate":
                return hierarchy_evaluate(args.audit, args.observed, args.pretty, args.json)
            if args.hierarchy_command == "compare":
                return hierarchy_compare(args.audit, args.observed, args.pretty, args.json)
            if args.hierarchy_command == "variants":
                return hierarchy_variants_command(args.audit, args.nominal, args.pairs, args.observed, args.json, args.pretty)
        if args.command == "assumptions":
            if args.assumptions_command == "inspect":
                return assumptions_inspect(args.system, args.pretty)
        if args.command == "preflight":
            if args.preflight_command == "review":
                return preflight_review(args.preflight, args.pretty, args.audit)
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
            if args.testfile_command in {'snapshot', 'series'}:
                from physicsguard.core.test_file_contract import testfile_snapshot, testfile_series
                import yaml
                output = (testfile_snapshot(args.contract, args.row) if args.testfile_command == 'snapshot'
                          else testfile_series(args.contract, args.rows))
                if args.out:
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(yaml.safe_dump(output, sort_keys=False), encoding='utf-8')
                else:
                    _print_json(output, args.pretty)
                return 0
            if args.testfile_command == "diff":
                return testfile_diff_command(args.old_contract, args.new_contract, args.pretty)
        if args.command == "validation":
            if args.validation_command == "run":
                return validation_run_command(args.plan, args.pretty, args.json)
    except Exception as exc:
        print(f"physicsguard error: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
