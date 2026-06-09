"""Command line interface for PhysicsGuard Core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.evaluator import AuditEvaluator
from physicsguard.core.hierarchy import HierarchicalAuditRunner, inspect_hierarchy, plan_from_report
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.io.yaml_loader import load_system_spec
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


def preflight_review(path: Path, pretty: bool = False) -> int:
    report = review_model_understanding_preflight(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


def intake_review(path: Path, pretty: bool = False) -> int:
    report = review_external_model_intake(path)
    _print_json(report.to_dict(), pretty)
    return 0 if report.ok else 1


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
            return project_command(args.project_command, args.root, args.pretty)
        if args.command == "preflight":
            if args.preflight_command == "review":
                return preflight_review(args.preflight, args.pretty)
        if args.command == "intake":
            if args.intake_command == "review":
                return intake_review(args.intake, args.pretty)
    except Exception as exc:
        print(f"physicsguard error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
