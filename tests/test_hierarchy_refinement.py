from __future__ import annotations

from physicsguard.core.diagnostics import ResidualDiagnostic
from physicsguard.core.hierarchy import BlockDiagnostic, RefinementPlanner
from physicsguard.schema.hierarchy_spec import HierarchySpec


def residual(key: str, role: str = "equation") -> ResidualDiagnostic:
    return ResidualDiagnostic(
        name=f"r.{key}",
        source="r",
        role=role,
        raw_value=2.0,
        scale=1.0,
        normalized_value=2.0,
        abs_normalized_value=2.0,
        diagnostic_key=key,
        description=None,
    )


def block(score: float = 2.0, key: str = "bad_key", role: str = "equation") -> BlockDiagnostic:
    return BlockDiagnostic(
        block_id="b",
        name=None,
        level=0,
        parent_id=None,
        tags=[],
        score=score,
        confidence=0.9,
        audit_pass=score <= 1.0,
        max_abs_normalized_residual=score,
        residual_norm=score,
        top_residuals=[residual(key, role)],
        post_check_residuals=[],
        missing_required_variables=[],
        missing_required_parameters=[],
        recommended_refinements=[],
    )


def hierarchy() -> HierarchySpec:
    return HierarchySpec.model_validate(
        {
            "blocks": [{"id": "b", "level": 0}],
            "refinement_rules": [
                {
                    "id": "low_priority",
                    "block_id": "b",
                    "trigger_diagnostic_keys": ["bad_key"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["detail_low"],
                    "priority": 1,
                },
                {
                    "id": "high_priority",
                    "block_id": "b",
                    "trigger_roles": ["equation"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["detail_high"],
                    "priority": 10,
                },
            ],
        }
    )


def test_rule_triggers_when_score_threshold_exceeded() -> None:
    recs = RefinementPlanner().recommended_refinements(block(), hierarchy())
    assert {rec.rule_id for rec in recs} == {"low_priority", "high_priority"}


def test_no_trigger_when_score_below_threshold() -> None:
    recs = RefinementPlanner().recommended_refinements(block(score=0.5), hierarchy())
    assert recs == []


def test_diagnostic_key_trigger_works() -> None:
    recs = RefinementPlanner().recommended_refinements(block(key="other"), hierarchy())
    assert [rec.rule_id for rec in recs] == ["high_priority"]


def test_role_trigger_works() -> None:
    recs = RefinementPlanner().recommended_refinements(block(role="boundary"), hierarchy())
    assert [rec.rule_id for rec in recs] == ["low_priority"]


def test_priority_ordering_works() -> None:
    recs = RefinementPlanner().recommended_refinements(block(), hierarchy())
    assert [rec.rule_id for rec in recs] == ["high_priority", "low_priority"]


def test_template_resolution_retains_every_id_and_never_executes_the_file(tmp_path) -> None:
    directory = tmp_path / "coolant_loop"
    directory.mkdir()
    (directory / "detail.yaml").write_text("not an audit: deliberately invalid, do not execute\n")
    spec = hierarchy()
    spec.refinement_rules[0].next_template_ids = ["b", "coolant_loop/detail", "detail.yaml", "radiator_missing"]
    recommendations = RefinementPlanner(directory).recommended_refinements(block(), spec)
    rec = next(item for item in recommendations if item.rule_id == "low_priority")
    assert rec.next_template_ids == spec.refinement_rules[0].next_template_ids
    assert rec.template_status == {"b": "block", "coolant_loop/detail": "file", "detail.yaml": "file", "radiator_missing": "planned"}
    assert RefinementPlanner().recommended_refinements(block(), spec)[1].template_status["b"] == "block"


def test_unbuilt_template_is_planned(tmp_path, monkeypatch) -> None:
    import builtins
    import io
    import os
    from pathlib import Path

    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io import hierarchy_loader, test_file_contract_loader, yaml_loader
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    # Build inputs/imports before the sentinel; stat/is_file is allowed, model reads are not.
    target = "future_subsystem"
    base = tmp_path / "audit"
    base.mkdir()
    candidates = {candidate.resolve() for parent in (base, base.parent)
                  for candidate in (parent / target, parent / (target + ".yaml"))}
    assert len(candidates) == 4 and all(not candidate.exists() for candidate in candidates)
    control = tmp_path / "unrelated.txt"
    control.write_text("ordinary reads remain allowed\n", encoding="utf-8")
    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "planned", "system": {"system_name": "planned", "components": [
            {"id": "coarse", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        ]}, "hierarchy": {"blocks": [{"id": "root", "components": ["coarse"]}], "refinement_rules": [
            {"id": "grow", "block_id": "root", "score_threshold": 1., "next_template_ids": [target]},
        ]},
    })
    observed = ObservedValuesSpec(variables={"coarse.x": {"value": 2., "unit": "1"}})
    before = spec.model_dump(mode="json"), observed.model_dump(mode="json")
    attempts, solver_calls = [], []

    def is_candidate(value):
        return (isinstance(value, (str, bytes, os.PathLike))
                and Path(os.fsdecode(value)).resolve() in candidates)

    def forbidden_loader(*args, **kwargs):
        attempts.append("model loader")
        raise AssertionError("a planned refinement is a recommendation, not a model to load")

    def guard_path_read(original):
        def checked(path, *args, **kwargs):
            if is_candidate(path):
                attempts.append(str(path))
                raise AssertionError("a planned candidate must not be read or executed")
            return original(path, *args, **kwargs)
        return checked

    def guard_raw_open(original):
        def checked(file, *args, **kwargs):
            if is_candidate(file):
                attempts.append(str(file))
                raise AssertionError("a planned candidate must not be opened")
            return original(file, *args, **kwargs)
        return checked

    def forbidden_solve(*args, **kwargs):
        solver_calls.append("solve")
        raise AssertionError("observed refinement planning must not solve")

    with monkeypatch.context() as patch:
        for module, name in ((hierarchy_loader, "load_hierarchical_audit_spec"),
                             (yaml_loader, "load_system_spec"),
                             (test_file_contract_loader, "load_yaml_mapping")):
            patch.setattr(module, name, forbidden_loader)
        for name in ("read_text", "read_bytes", "open"):
            patch.setattr(Path, name, guard_path_read(getattr(Path, name)))
        patch.setattr(builtins, "open", guard_raw_open(builtins.open))
        patch.setattr(io, "open", guard_raw_open(io.open))
        patch.setattr(BoundedSolver, "solve", forbidden_solve)
        assert not (base / target).is_file()  # availability checks are deliberately permitted
        assert control.read_text(encoding="utf-8") == "ordinary reads remain allowed\n"
        report = HierarchicalAuditRunner(spec, base_dir=base).evaluate_observed(observed)

    # Even a reader which swallowed the sentinel exception cannot claim a pass.
    assert attempts == [] and solver_calls == []
    assert (spec.model_dump(mode="json"), observed.model_dump(mode="json")) == before
    assert report.audit_pass is False and report.checked_residuals
    assert report.metadata["solver_attempted"] is False
    recommendation, = report.recommended_refinements
    assert recommendation.rule_id == "grow" and recommendation.next_template_ids == [target]
    assert recommendation.template_status == {target: "planned"}


def test_shipped_refinement_pointers_resolve() -> None:
    from pathlib import Path
    import yaml

    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    examples = Path(__file__).resolve().parents[1] / "examples"
    for audit in examples.rglob("*.yaml"):
        data = yaml.safe_load(audit.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "system" not in data or "hierarchy" not in data:
            continue
        spec = load_hierarchical_audit_spec(audit)
        planner = RefinementPlanner(audit.parent)
        for rule in spec.hierarchy.refinement_rules:
            for template_id in rule.next_template_ids:
                status = planner._template_status(template_id, spec.hierarchy)
                assert status in {"block", "file", "planned"}, (audit, rule.id, template_id)
                if status == "planned":
                    # A shipped target must say what to measure first.
                    assert rule.next_required_variables, (audit, rule.id, template_id)
