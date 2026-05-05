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
    except Exception as exc:
        print(f"physicsguard error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
