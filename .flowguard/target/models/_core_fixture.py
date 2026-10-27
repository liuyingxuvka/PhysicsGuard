"""Native audit fixtures and pure stage facts; this file is not an executable model."""
from __future__ import annotations
from dataclasses import dataclass,replace
from contextlib import contextmanager
from pathlib import Path
import sys
import dataclasses
ROOT=Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class AuditInput:
    case_id: str
    valid_schema: bool
    finite_bounded_variables: bool
    known_references: bool
    normalized_residuals: bool
    solver_converges: bool
    residual_within_threshold: bool
    has_post_check_residuals: bool = False
    post_check_enters_solver: bool = False
    mode: str = "hierarchy_run"
    observed_values_complete: bool = True
    has_assumptions: bool = False
    parameter_assumption: bool = False
    variable_assumption: bool = False
    assumption_override: bool = False
    proposed_assumption: bool = False
    rejected_assumption: bool = False
    assumption_as_free_variable: bool = False
    unobserved_zero_product: bool = False

ASSUMPTION_LABELS = {
    "parameter_fill": "parameter_assumption_filled",
    "parameter_override": "assumption_override_warned",
    "not_applied_proposed": "proposed_assumption_not_applied",
    "not_applied_rejected": "rejected_assumption_not_applied",
    "boundary_residual": "variable_assumption_boundary_ready",
}

PITCH = "examples/hierarchical/observed_debugging"

EXTERNAL_INPUTS = (
    AuditInput("clean", True, True, True, True, True, True),
    AuditInput("converged_bad_audit", True, True, True, True, True, False),
    AuditInput("bad_bounds", True, False, True, True, True, True),
    AuditInput("unknown_ref", True, True, False, True, True, True),
    AuditInput("raw_residual", True, True, True, False, True, True),
    AuditInput("post_check_diagnostic_only", True, True, True, True, True, True, True, False),
    AuditInput("post_check_bad_selection", True, True, True, True, True, True, True, True),
    AuditInput("evaluate_clean", True, True, True, True, True, True, False, False, "hierarchy_evaluate", True),
    AuditInput("evaluate_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_evaluate", True),
    AuditInput("evaluate_missing_observed", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("compare_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_compare", True),
    AuditInput("hierarchy_clean", True, True, True, True, True, True, False, False, "hierarchy_run", True),
    AuditInput("hierarchy_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_run", True),
    AuditInput("hierarchy_evaluate_clean", True, True, True, True, True, True, False, False, "hierarchy_evaluate", True),
    AuditInput("hierarchy_evaluate_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_evaluate", True),
    AuditInput("hierarchy_evaluate_missing_observed", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("hierarchy_evaluate_derived_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate", observed_values_complete=False),
    AuditInput("hierarchy_evaluate_derived_child_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate", observed_values_complete=False),
    AuditInput("hierarchy_evaluate_partial_unresolved", True, True, True, True, True, True, mode="hierarchy_evaluate", observed_values_complete=False),
    AuditInput("hierarchy_evaluate_partial_snapshot", True, True, True, True, True, True, False, False, "hierarchy_evaluate", False),
    AuditInput("hierarchy_evaluate_zero_product", True, True, True, True, True, True, mode="hierarchy_evaluate", observed_values_complete=False, unobserved_zero_product=True),
    AuditInput("hierarchy_compare_bad_audit", True, True, True, True, True, False, False, False, "hierarchy_compare", True),
    AuditInput("hierarchy_describe", True, True, True, True, True, True, False, False, "hierarchy_describe", True),
    AuditInput("assumption_parameter_fill", True, True, True, True, True, True, has_assumptions=True, parameter_assumption=True),
    AuditInput("assumption_variable_boundary", True, True, True, True, True, True, has_assumptions=True, variable_assumption=True),
    AuditInput("assumption_parameter_override", True, True, True, True, True, True, has_assumptions=True, parameter_assumption=True, assumption_override=True),
    AuditInput("assumption_proposed", True, True, True, True, True, True, has_assumptions=True, proposed_assumption=True),
    AuditInput("assumption_rejected", True, True, True, True, True, True, has_assumptions=True, rejected_assumption=True),
    AuditInput("assumption_context", True, True, True, True, True, True, has_assumptions=True),
    AuditInput("assumption_free_variable", True, True, True, True, True, True, has_assumptions=True, assumption_as_free_variable=True),
    AuditInput("no_converge", True, True, True, True, False, True),
    AuditInput("bad_schema", False, True, True, True, True, True),
    AuditInput("growth_coarse_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate"),
    AuditInput("growth_planned_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate"),
    AuditInput("hierarchy_evaluate_partial_tree_view_bad_audit", True, True, True, True, True, False, mode="hierarchy_evaluate", observed_values_complete=False),
)

class ReplayReport:
    """Conformance result: how many model cases were replayed on the real code, and the mismatches."""

    def __init__(self, checked: int, mismatches: list[str]) -> None:
        self.checked = checked
        self.mismatches = tuple(mismatches)
        self.ok = not self.mismatches

    def format_text(self, max_examples: int | None = None) -> str:
        lines = [f"conformance: {self.checked - len(self.mismatches)}/{self.checked} model cases match the real code"]
        examples = list(self.mismatches[:max_examples])
        for mismatch in self.mismatches:
            if "real replay raised " in mismatch and mismatch not in examples:
                examples.append(mismatch)
        return "\n".join(lines + [f"  mismatch: {line}" for line in examples])

EXTERNAL_INPUTS += (AuditInput('hierarchy_evaluate_partial_tree_view_not_checked',True,True,True,True,True,True,mode='hierarchy_evaluate',observed_values_complete=False),)


@contextmanager
def _solver_counted():
    from physicsguard.core.solver import BoundedSolver

    calls = []
    original = BoundedSolver.solve

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    BoundedSolver.solve = counting
    try:
        yield calls
    finally:
        BoundedSolver.solve = original


def _hierarchy(mode: str, audit_file: str, observed_file: str | None = None, keep: int | None = None):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    spec = load_hierarchical_audit_spec(ROOT / audit_file)
    with _solver_counted() as calls:
        if mode == "describe":
            describe_hierarchy(spec)
            return ("hierarchy_described_without_solver" if not calls else "solver_attempted"), None
        if mode == "run":
            report = HierarchicalAuditRunner(spec).run()
            if not calls:
                return "no_solver_call", report.audit_pass
            label = (
                "optimizer_converged_audit_failed"
                if report.optimization_success and not report.audit_pass
                else "hierarchy_run_solved_and_reported"
            )
            return label, report.audit_pass
        if mode not in {"evaluate", "compare"}:
            raise ValueError(f"unsupported replay mode: {mode}")
        observed = load_observed_values(ROOT / observed_file)
        if keep is not None:
            observed = observed.model_copy(update={"variables": dict(list(observed.variables.items())[:keep])})
        before = observed.model_dump(mode="json")
        try:
            if mode == "compare":
                report = HierarchicalAuditRunner(spec).compare_observed(observed)
                assert observed.model_dump(mode="json") == before
                assert calls, "comparison requires a reference solve"
                assert report.reference_optimization_success
                assert report.reference_audit_pass
                assert report.reference_variables and report.observed_variables
                return "hierarchy_compare_solved_and_evaluated", report.observed_audit_pass
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
        except ValueError as exc:
            assert observed.model_dump(mode="json") == before
            if mode == "evaluate":
                assert not calls, "observed evaluation must not solve"
                if "no residual can be evaluated without them" in str(exc):
                    return "no_independent_observed_check_failed", None
            raise
        assert observed.model_dump(mode="json") == before
    if keep is not None and report.derived_variables:
        assert report.checked_residuals, "derived values alone are not independent checks"
        assert not set(report.metadata["derivation_residual_occurrences"]) & set(report.metadata["checked_residual_occurrences"])
        return ("derived_relations_excluded_from_checks" if not calls else "solver_attempted"), report.audit_pass
    return ("hierarchy_observed_evaluated_without_solver" if not calls else "solver_attempted"), report.audit_pass


def _coolant_declared_fault_run() -> tuple[str, bool]:
    """Replay the existing underread on the same connected tree, without a copy."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec

    directory = ROOT / "examples/hierarchical/coolant_loop"
    spec = load_hierarchical_audit_spec(directory / "tree.yaml")
    nominal = load_observed_values(directory / "nominal_observed.yaml")
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")
    variant = next(v for v in spec.fault_variants if v.id == "heat_rejection")
    change, = variant.changes
    assert change.scale is not None and not variant.parameters and not variant.rederive
    data = spec.model_dump(mode="json")
    boundary = next(row for row in data["system"]["boundaries"] if row["variable"] == change.variable)
    boundary["value"] = nominal.variables[change.variable].value * change.scale
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(HierarchicalAuditSpec.model_validate(data), directory).run()
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before
    if not calls:
        return "no_solver_call", report.audit_pass
    return ("optimizer_converged_audit_failed" if report.optimization_success and not report.audit_pass
            else "hierarchy_run_solved_and_reported"), report.audit_pass


def _partial_snapshot(audit_file: str, unobserved: str) -> tuple[str, bool]:
    """The CLI path: a solved snapshot without one variable, evaluated with skip_unobserved."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = load_hierarchical_audit_spec(ROOT / audit_file)
    solved = BoundedSolver(ResidualBuilder(spec.system), spec.system.solver).solve().variables
    observed = ObservedValuesSpec(variables={name: {"value": value} for name, value in solved.items() if name != unobserved})
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    listed = unobserved in report.missing_required_variables and bool(report.unchecked_residuals)
    derived = report.derived_variables.get(unobserved)
    if derived and derived["residual_occurrence"] not in report.metadata["checked_residual_occurrences"] and not calls:
        return "unobserved_values_derived", report.audit_pass
    label = "unobserved_residuals_skipped" if listed and not calls else "unobserved_residuals_hidden"
    return label, report.audit_pass


def _derived_tank_snapshot() -> tuple[str, bool]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    example = ROOT / "examples/hierarchical/heated_tank"
    sparse = example / "sparse_measured_k70.yaml"
    assert sparse.is_file(), f"new sparse snapshot is not implemented: {sparse}"
    spec = load_hierarchical_audit_spec(example / "heated_tank.yaml")
    observed = load_observed_values(sparse)
    before = observed.model_dump(mode="json")
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    used = set(report.metadata["derivation_residual_occurrences"])
    checked = set(report.metadata["checked_residual_occurrences"])
    thermal = any(block.block_id in {"tank", "thermal"} and not block.own_audit_pass for block in report.top_blocks) and not report.audit_pass
    heater = any("heater" in rec.next_template_ids and rec.template_status.get("heater") == "block" for rec in report.recommended_refinements)
    valid = used and checked and not used & checked and report.derived_variables and thermal and heater
    valid = valid and not calls and observed.model_dump(mode="json") == before
    return ("derived_relations_excluded_from_checks" if valid else "derived_relations_misreported"), report.audit_pass


def _unresolved_partial_snapshot() -> tuple[str, bool]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    parameters = {"a": 1., "b": 0., **{f"{axis}_{key}": value for axis in ("x", "y")
                  for key, value in (("lower_bound", -100.), ("upper_bound", 100.), ("initial_guess", 0.), ("scale", 1.))}}
    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "partial", "system": {"system_name": "partial", "components": [
            {"id": "unseen", "type": "LinearRelationModule", "parameters": parameters},
            {"id": "known", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        ]}, "hierarchy": {"blocks": [{"id": "plant", "level": 0, "components": ["unseen", "known"]}]},
    })
    observed = ObservedValuesSpec(variables={"known.x": {"value": 0.}})
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
    listed = report.missing_required_variables == ["unseen.x", "unseen.y"] and bool(report.unchecked_residuals)
    return ("unobserved_residuals_skipped" if listed and not calls else "unobserved_residuals_hidden"), report.audit_pass


def _child_failure_snapshot() -> tuple[str, bool]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    example = ROOT / "examples/hierarchical/heated_tank"
    observed = load_observed_values(example / "measured_k70.yaml")
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(load_hierarchical_audit_spec(example / "heated_tank.yaml")).evaluate_observed(observed)
    blocks = {block.block_id: block for block in report.top_blocks}
    own_failures = [block for block in report.top_blocks if not block.own_audit_pass]
    valid = not calls and not report.audit_pass and max(own_failures, key=lambda block: block.level).block_id == "heater"
    valid = valid and all(not blocks[name].audit_pass for name in ("heater", "thermal", "tank"))
    valid = valid and blocks["hydraulics"].audit_pass
    return "child_failure_propagated" if valid else "child_failure_hidden", report.audit_pass


def _zero_product_snapshot() -> tuple[str, bool | None]:
    """An electrical zero product supplies no independently evaluable residual."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "zero_product",
        "system": {"system_name": "power", "components": [{
            "id": "power", "type": "ElectricalPowerModule",
            "parameters": {"V_initial_guess": 0.0, "current_initial_guess": 0.0, "P_initial_guess": 0.0},
        }]},
        "hierarchy": {"blocks": [{"id": "power_block", "name": "power", "level": 0,
            "components": ["power"], "required_variables": ["power.V_V", "power.current_A", "power.P_W"]}]},
    })
    observed = ObservedValuesSpec(variables={"power.P_W": {"value": 0.0, "unit": "W"}})
    before = observed.model_dump(mode="json")
    with _solver_counted() as calls:
        try:
            report = HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True)
        except ValueError as exc:
            if "no residual can be evaluated without them" not in str(exc):
                raise
            assert not calls, "partial observations must not solve"
            assert observed.model_dump(mode="json") == before
            return "no_independent_observed_check_failed", None
    assert observed.model_dump(mode="json") == before
    return ("solver_attempted" if calls else "residual_evaluated_from_unobserved_guess"), report.audit_pass


def _bad_schema() -> tuple[str, None]:
    from pydantic import ValidationError

    from physicsguard.schema.system_spec import SystemSpec

    try:
        SystemSpec.model_validate({"system_name": "missing_components"})
    except ValidationError:
        return "schema_failed", None
    return "schema_valid", None


def _assumption(relative: str) -> tuple[str, None]:
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.io.yaml_loader import load_system_spec

    summary = ResidualBuilder(load_system_spec(ROOT / relative)).assumption_summary()
    return ASSUMPTION_LABELS.get(summary.cards[0].application, summary.cards[0].application), None


def _growth_coarse_report() -> tuple[str, bool]:
    """Framework-only two-relation witness; no claim of a physical module."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({"audit_name": "growth", "system": {"system_name": "growth", "components": [
        {"id": name, "type": "DummyResidualModule", "parameters": {"target": 0.}} for name in ("coarse", "fine")
    ]}, "hierarchy": {"blocks": [
        {"id": "parent", "components": ["coarse"]},
        {"id": "child", "parent_id": "parent", "level": 1, "components": ["fine"], "refines": ["coarse"]},
    ]}})
    observed = ObservedValuesSpec(variables={"coarse.x": {"value": 2.}, "fine.x": {"value": 0.}})
    before = observed.model_dump(mode="json")
    with _solver_counted() as calls:
        report = HierarchicalAuditRunner(spec).evaluate_observed(observed)
    row, = report.refinement_checks
    assert row["coarse_pass"] is False and row["children_pass"] is True and row["consistent"] is False
    assert "refinement_inconsistent: parent" in report.warnings
    assert not calls and observed.model_dump(mode="json") == before
    return "coarse_failure_consistency_reported", report.audit_pass


def _growth_planned_report() -> tuple[str, bool]:
    import builtins
    import io
    import os
    from tempfile import TemporaryDirectory
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec
    from physicsguard.io import hierarchy_loader, yaml_loader, test_file_contract_loader

    target = "future_subsystem"
    spec = HierarchicalAuditSpec.model_validate({"audit_name": "planned", "system": {"system_name": "planned", "components": [
        {"id": "coarse", "type": "DummyResidualModule", "parameters": {"target": 0.}},
    ]}, "hierarchy": {"blocks": [{"id": "root", "components": ["coarse"]}], "refinement_rules": [
        {"id": "grow", "block_id": "root", "score_threshold": 1., "next_template_ids": [target]},
    ]}})
    observed = ObservedValuesSpec(variables={"coarse.x": {"value": 2.}})
    before = observed.model_dump(mode="json")
    attempts = []
    restores = []
    with TemporaryDirectory() as directory:
        base = Path(directory) / "audit"
        base.mkdir()
        candidates = {candidate.resolve() for parent in (base, base.parent) for candidate in (parent / target, parent / (target + ".yaml"))}
        assert len(candidates) == 4 and all(not candidate.exists() for candidate in candidates)
        def is_candidate(value):
            return isinstance(value, (str, bytes, os.PathLike)) and Path(os.fsdecode(value)).resolve() in candidates
        def forbidden_loader(*args, **kwargs):
            attempts.append(("loader", str(args[0]) if args else str(kwargs)))
            raise AssertionError("refinement suggestions must not load a model")
        def guard_method(original):
            def checked(self, *args, **kwargs):
                if is_candidate(self):
                    attempts.append(("path", str(self)))
                    raise AssertionError("planned candidate must not be read or executed")
                return original(self, *args, **kwargs)
            return checked
        def guard_raw_open(original):
            def checked(file, *args, **kwargs):
                if is_candidate(file):
                    attempts.append(("open", str(file)))
                    raise AssertionError("planned candidate must not be opened")
                return original(file, *args, **kwargs)
            return checked
        for owner, name in [(hierarchy_loader, "load_hierarchical_audit_spec"), (yaml_loader, "load_system_spec"), (test_file_contract_loader, "load_yaml_mapping")]:
            restores.append((owner, name, getattr(owner, name)))
            setattr(owner, name, forbidden_loader)
        for name in ("read_text", "read_bytes", "open"):
            restores.append((Path, name, getattr(Path, name)))
            setattr(Path, name, guard_method(getattr(Path, name)))
        for owner in (builtins, io):
            restores.append((owner, "open", owner.open))
            owner.open = guard_raw_open(owner.open)
        try:
            with _solver_counted() as solver_calls:
                report = HierarchicalAuditRunner(spec, base_dir=base).evaluate_observed(observed)
        finally:
            for owner, name, original in reversed(restores):
                setattr(owner, name, original)
    assert not attempts and not solver_calls and observed.model_dump(mode="json") == before
    rec, = report.recommended_refinements
    assert rec.next_template_ids == [target] and rec.template_status == {target: "planned"}
    return "planned_template_reported_not_executed", report.audit_pass


def _tree_view_report() -> tuple[str, bool]:
    """Render the sparse heated-tank evaluation; every block line carries the report's verdict."""
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
    from physicsguard.core.tree_view import render_tree_view
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    tank = ROOT / "examples/hierarchical/heated_tank"
    spec = load_hierarchical_audit_spec(tank / "heated_tank.yaml")
    runner = HierarchicalAuditRunner(spec, base_dir=tank)
    with _solver_counted() as calls:
        report = runner.to_dict(runner.evaluate_observed(load_observed_values(tank / "sparse_measured_k70.yaml"), skip_unobserved=True))
        text = render_tree_view(describe_hierarchy(spec, base_dir=tank), report=report)
    assert not calls
    lines = {line.split(" [L")[0].strip(): line for line in text.splitlines() if " [L" in line}
    assert set(lines) == {row["block_id"] for row in report["block_verdicts"]} == {block.id for block in spec.hierarchy.blocks}
    for row in report["block_verdicts"]:
        line = lines[row["block_id"]]
        if row["checked_residual_count"]:
            assert f"own {'PASS' if row['own_audit_pass'] else 'FAIL'} " in line, line
        else:
            assert "PASS" not in line.split(" | ")[-1], line
        assert ("not checked: " in line) is bool(row["missing_required_variables"]), line
    return "tree_view_rendered_with_block_verdicts", report["audit_pass"]

REAL_CASES = {
    "growth_coarse_bad_audit": _growth_coarse_report,
    "growth_planned_bad_audit": _growth_planned_report,
    "hierarchy_evaluate_partial_tree_view_bad_audit": _tree_view_report,
    "hierarchy_evaluate_derived_child_bad_audit": _child_failure_snapshot,
    "hierarchy_evaluate_derived_bad_audit": _derived_tank_snapshot,
    "hierarchy_evaluate_partial_unresolved": _unresolved_partial_snapshot,
    "clean": lambda: _hierarchy("run", "examples/dummy_system.yaml"),
    "converged_bad_audit": lambda: _hierarchy("run", "examples/dummy_conflict_system.yaml"),
    "bad_schema": _bad_schema,
    "evaluate_clean": lambda: _hierarchy("evaluate", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml"),
    "evaluate_bad_audit": lambda: _hierarchy("evaluate", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_conflict.yaml"),
    "evaluate_missing_observed": lambda: _hierarchy("evaluate", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_clean.yaml", keep=1),
    "compare_bad_audit": lambda: _hierarchy("compare", "examples/physical_coolant_heat_balance.yaml", "examples/observed/physical_coolant_observed_conflict.yaml"),
    "hierarchy_clean": lambda: _hierarchy("run", "examples/hierarchical/coolant_loop/tree.yaml"),
    "hierarchy_bad_audit": lambda: _coolant_declared_fault_run(),
    "hierarchy_evaluate_clean": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml"),
    "hierarchy_evaluate_bad_audit": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_fault.yaml"),
    "hierarchy_evaluate_missing_observed": lambda: _hierarchy("evaluate", f"{PITCH}/pitch_feedback_level_0.yaml", f"{PITCH}/pitch_feedback_observed_clean.yaml", keep=1),
    "hierarchy_evaluate_zero_product": _zero_product_snapshot,
    "hierarchy_evaluate_partial_snapshot": lambda: _partial_snapshot("examples/hierarchical/coolant_loop/tree.yaml", "cool.Q_stack_heat_W"),
    "hierarchy_describe": lambda: _hierarchy("describe", f"{PITCH}/pitch_feedback_level_0.yaml"),
    "assumption_parameter_fill": lambda: _assumption("examples/assumptions/parameter_assumption.yaml"),
    "assumption_parameter_override": lambda: _assumption("examples/assumptions/parameter_override_warning.yaml"),
    "assumption_proposed": lambda: _assumption("examples/assumptions/proposed_assumption.yaml"),
    "assumption_rejected": lambda: _assumption("examples/assumptions/rejected_assumption.yaml"),
    "assumption_variable_boundary": lambda: _assumption("examples/assumptions/variable_assumption.yaml"),
}


def _root_not_checked():
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec
    spec=HierarchicalAuditSpec.model_validate({'audit_name':'partial-root','system':{'system_name':'partial-root','components':[{'id':'power','type':'ElectricalPowerModule','parameters':{'V_initial_guess':0.,'current_initial_guess':0.,'P_initial_guess':0.}},{'id':'fine','type':'DummyResidualModule','parameters':{'target':0.}}]},'hierarchy':{'blocks':[{'id':'root','level':0,'components':['power'],'required_variables':['power.V_V','power.current_A','power.P_W']},{'id':'child','parent_id':'root','level':1,'components':['fine']}]}})
    report=HierarchicalAuditRunner(spec).evaluate_observed(ObservedValuesSpec(variables={'power.P_W':{'value':0.,'unit':'W'},'fine.x':{'value':0.}}),skip_unobserved=True)
    rows=HierarchicalAuditRunner(spec).to_dict(report)['block_verdicts']
    root=next(row for row in rows if row['level']==0)
    assert not root['checked_residual_count'] and root['missing_required_variables']
    assert next(row for row in rows if row['block_id']=='child')['own_audit_pass']
    return 'tree_view_rendered_with_block_verdicts',report.audit_pass

REAL_CASES['hierarchy_evaluate_partial_tree_view_not_checked']=_root_not_checked


def stage_facts(case):
    """Only coarse pipeline markers, computed from the declared AuditInput."""
    key=case.case_id
    schema=case.valid_schema
    registry=schema and 'bad_bounds' not in key and not case.assumption_as_free_variable
    partial=(case.mode=='hierarchy_evaluate' and not case.observed_values_complete and
             ('partial' in key or 'derived' in key or key=='evaluate_missing_observed'))
    missing=case.mode in ('hierarchy_evaluate','hierarchy_compare') and not case.observed_values_complete and not partial
    assembled=registry and 'unknown_ref' not in key and 'raw_residual' not in key and not case.post_check_enters_solver and not missing
    described=assembled and case.mode=='hierarchy_describe'
    normalized=assembled and not described
    executed=assembled and case.mode in ('hierarchy_evaluate','hierarchy_compare','hierarchy_run')
    values={'schema_valid':schema,'registry_valid':registry,'residuals_normalized':normalized,
            'solve_attempted':executed and case.mode!='hierarchy_evaluate',
            'comparisons':executed and case.mode=='hierarchy_compare',
            'hierarchy_reports':executed,'hierarchy_descriptions':described,
            'diagnostics_emitted':executed or described,'failures':not assembled}
    return {name:(key,) if value else () for name,value in values.items()}

def _plain(value):
 if hasattr(value,'model_dump'):return value.model_dump(mode='json')
 if dataclasses.is_dataclass(value):return dataclasses.asdict(value)
 return value

def replay_case(case):
 from physicsguard.core.hierarchy import HierarchicalAuditRunner
 from physicsguard.core.residual import ResidualBuilder
 reports=[];summaries=[];restores=[]
 def capture(owner,name,dest):
  original=getattr(owner,name)
  def wrapped(*args,**kwargs):
   result=original(*args,**kwargs);dest.append((name,_plain(result)));return result
  restores.append((owner,name,original));setattr(owner,name,wrapped)
 for name in ('run','evaluate_observed','compare_observed'):capture(HierarchicalAuditRunner,name,reports)
 capture(ResidualBuilder,'assumption_summary',summaries)
 try:label,audit=REAL_CASES[case]()
 finally:
  for owner,name,original in reversed(restores):setattr(owner,name,original)
 report=reports[-1][1] if reports else {}
 assumptions=report.get('assumptions') or (summaries[-1][1] if summaries else {})
 observed='not_observed'
 if reports and reports[-1][0] in ('evaluate_observed','compare_observed'):
  observed='unobserved_listed' if report.get('unchecked_residuals') else 'evaluated'
 disposition='none'
 if assumptions.get('cards'):
  disposition='override_warned' if any('parameter' in warning and 'overridden' in warning for warning in assumptions.get('warnings',[])) else 'applied' if assumptions.get('applied_count',0)>0 else 'not_applied'
 roots=[row for row in report.get('block_verdicts',[]) if row['level']==0]
 verdict='no checks'
 if roots:
  root=roots[0];verdict=('PASS' if root['own_audit_pass'] else 'FAIL') if root['checked_residual_count'] else 'not checked' if root['missing_required_variables'] else 'no checks'
 audit_status='not_run'
 if reports and reports[-1][0] in ('run','compare_observed'):
  passed=report.get('reference_audit_pass') if reports[-1][0]=='compare_observed' else report.get('audit_pass')
  audit_status='passed' if passed else 'failed'
 return label,audit,(observed,disposition,verdict,audit_status),report,assumptions



def replay_assumption_report(case_id):
    """Check actual diagnostic card preservation, beyond the legacy summary label."""
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.core.diagnostics import DiagnosticReporter
    from physicsguard.io.yaml_loader import load_system_spec
    paths={'assumption_parameter_fill':'parameter_assumption.yaml','assumption_parameter_override':'parameter_override_warning.yaml',
           'assumption_proposed':'proposed_assumption.yaml','assumption_rejected':'rejected_assumption.yaml','assumption_variable_boundary':'variable_assumption.yaml'}
    spec=load_system_spec(ROOT/'examples/assumptions'/paths[case_id]);builder=ResidualBuilder(spec)
    cards=builder.assumption_cards()
    report=DiagnosticReporter().generate(spec,builder,BoundedSolver(builder,spec.solver).solve())
    assert {card.id for card in cards}=={card.id for card in report.assumptions.cards}
    return report
