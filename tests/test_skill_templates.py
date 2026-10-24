from __future__ import annotations

from pathlib import Path


from physicsguard.workflow import review_model_understanding_preflight


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"


def test_installed_model_and_snapshot_templates_keep_an_independent_native_check(tmp_path: Path) -> None:
    import importlib.util
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    path = ROOT / "scripts/install_physicsguard_skills.py"
    spec = importlib.util.spec_from_file_location("pg_template_installer", path)
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    installer.install(SKILL_ROOT, tmp_path)
    installed = tmp_path / "physicsguard/references"
    assert (installed / "model-format.md").is_file()
    audit = load_hierarchical_audit_spec(installed / "templates/audit_model.yaml")
    observed = load_observed_values(installed / "templates/observed_snapshot.yaml")
    before = observed.model_dump()
    report = HierarchicalAuditRunner(audit).evaluate_observed(observed)
    assert report.audit_pass and report.checked_residuals
    assert not report.derived_variables
    assert observed.model_dump() == before
    assert len(audit.hierarchy.blocks) == 2
    assert not installer.pending_changes(SKILL_ROOT, tmp_path)


def test_skill_preflight_template_passes_its_review() -> None:
    templates = SKILL_ROOT / "physicsguard" / "references" / "templates"
    assert review_model_understanding_preflight(templates / "model_understanding_preflight.yaml").status == "pass"
