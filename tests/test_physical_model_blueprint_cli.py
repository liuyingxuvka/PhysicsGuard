from __future__ import annotations

import json
from pathlib import Path

import yaml

import physicsguard.cli as physicsguard_cli
from physicsguard.cli import main


def _write_blueprints(blueprint, root: Path) -> tuple[Path, Path]:
    data = blueprint.model_dump(mode="json", exclude_none=True)
    yaml_path = root / "pump_loop_blueprint.yaml"
    json_path = root / "pump_loop_blueprint.json"
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return yaml_path, json_path


def _authority_args(complete_physical_blueprint) -> list[str]:
    return [
        "--target-authority",
        str(complete_physical_blueprint.target_inventory_authority_path),
    ]


def test_canonical_yaml_and_json_cli_have_same_logical_result(
    complete_physical_blueprint,
    capsys,
) -> None:
    blueprint, root = complete_physical_blueprint()
    yaml_path, json_path = _write_blueprints(blueprint, root)
    before = sorted(path.relative_to(root) for path in root.rglob("*"))

    authority_args = _authority_args(complete_physical_blueprint)
    assert main(["blueprint", "review", str(yaml_path), *authority_args]) == 0
    yaml_report = json.loads(capsys.readouterr().out)
    assert main(["blueprint", "review", str(json_path), *authority_args, "--pretty"]) == 0
    json_report = json.loads(capsys.readouterr().out)

    assert yaml_report == json_report
    assert yaml_report["logical_report_fingerprint"] == json_report["logical_report_fingerprint"]
    assert sorted(path.relative_to(root) for path in root.rglob("*")) == before


def test_cli_rejects_unknown_schema_without_fallback(tmp_path: Path, capsys) -> None:
    path = tmp_path / "retired.yaml"
    path.write_text("schema_version: physicsguard.physical-model-blueprint.v0\n", encoding="utf-8")

    assert main(
        [
            "blueprint",
            "review",
            str(path),
            "--target-authority",
            str(path),
        ]
    ) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["category"] == "unsupported_schema"
    assert output["status"] == "invalid"


def test_cli_distinguishes_incomplete_stale_and_missing_native_artifact(
    complete_physical_blueprint,
    capsys,
) -> None:
    blueprint, root = complete_physical_blueprint()
    authority_args = _authority_args(complete_physical_blueprint)

    incomplete = blueprint.model_dump(mode="json")
    incomplete["refinements"][0]["port_mappings"] = incomplete["refinements"][0]["port_mappings"][1:]
    incomplete_path = root / "incomplete.json"
    incomplete_path.write_text(json.dumps(incomplete), encoding="utf-8")
    assert main(["blueprint", "review", str(incomplete_path), *authority_args]) == 3
    capsys.readouterr()

    stale = blueprint.model_dump(mode="json")
    stale["bindings"][0]["status"] = "stale"
    stale_path = root / "stale.json"
    stale_path.write_text(json.dumps(stale), encoding="utf-8")
    assert main(["blueprint", "review", str(stale_path), *authority_args]) == 4
    capsys.readouterr()

    (root / "artifacts" / "implementation.txt").unlink()
    current_path = root / "missing.json"
    current_path.write_text(json.dumps(blueprint.model_dump(mode="json")), encoding="utf-8")
    assert main(["blueprint", "review", str(current_path), *authority_args]) == 5
    output = json.loads(capsys.readouterr().out)
    assert any(gap["code"] == "native_binding_not_current" for gap in output["gaps"])


def test_blueprint_cli_has_no_check_validate_or_inspect_aliases(capsys) -> None:
    for alias in ("check", "validate", "inspect"):
        try:
            main(["blueprint", alias, "ignored.yaml"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError(f"unexpected blueprint alias accepted: {alias}")
        capsys.readouterr()


def test_blueprint_review_help_names_first_gap_and_read_only_claim_boundary(capsys) -> None:
    try:
        main(["blueprint", "review", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("argparse help should exit after rendering")

    output = " ".join(capsys.readouterr().out.split())
    assert "first actionable gap" in output
    assert "make no writes" in output
    assert "do not claim that the target is reconstructable" in output
    assert "--target-authority" in output
    assert "--material-root" in output
    assert "--provider-registry" not in output


def test_explicit_material_root_is_not_implicitly_followed(
    complete_physical_blueprint,
    capsys,
) -> None:
    blueprint, root = complete_physical_blueprint()
    data = blueprint.model_dump(mode="json", exclude_none=False)
    data["artifact_root"] = "explicit_material_root"
    blueprint_path = root / "portable_descriptor.json"
    blueprint_path.write_text(json.dumps(data), encoding="utf-8")
    authority_args = _authority_args(complete_physical_blueprint)

    assert main(["blueprint", "review", str(blueprint_path), *authority_args]) == 5
    not_run = json.loads(capsys.readouterr().out)
    assert not_run["status"] == "blocked"
    assert not_run["gaps"][0]["code"] == "external_resource_not_run"
    assert "no target bytes or native owner were executed" in not_run["gaps"][0]["message"]

    assert main(
        [
            "blueprint",
            "review",
            str(blueprint_path),
            *authority_args,
            "--material-root",
            str(root),
        ]
    ) == 0
    executed = json.loads(capsys.readouterr().out)
    assert executed["status"] == "pass"
    assert executed["gaps"] == []


def test_blueprint_cli_internal_failure_has_distinct_exit(
    monkeypatch,
    capsys,
) -> None:
    def _unexpected_failure(_path):
        raise RuntimeError("unexpected reviewer failure")

    monkeypatch.setattr(
        physicsguard_cli,
        "load_physical_model_blueprint",
        _unexpected_failure,
    )

    assert main(
        [
            "blueprint",
            "review",
            "blueprint.yaml",
            "--target-authority",
            "authority.yaml",
        ]
    ) == 1
    assert "unexpected reviewer failure" in capsys.readouterr().err
