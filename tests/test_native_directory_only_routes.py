from __future__ import annotations

import json
from pathlib import Path

import pytest

import physicsguard
from physicsguard.cli import main


def test_public_disk_bundle_routes_are_hard_blocked_without_writing(tmp_path: Path, capsys) -> None:
    output = tmp_path / "portable-dna.json"
    code = main(
        [
            "blueprint",
            "bundle-export",
            str(tmp_path / "blueprint.json"),
            "--target-authority",
            str(tmp_path / "authority.json"),
            "--output",
            str(output),
        ]
    )

    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "native_directory_only"
    assert payload["status"] == "blocked"
    assert not output.exists()
    with pytest.raises(AttributeError):
        getattr(physicsguard, "load_physical_blueprint_export_bundle")


def test_self_dna_has_no_export_route(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["self-dna", "export", "--output", "unused.json"])
    assert "invalid choice" in capsys.readouterr().err


def test_compact_self_dna_preserves_first_gap_and_boundary(tmp_path: Path, capsys) -> None:
    code = main(["self-dna", "check", "--root", str(tmp_path), "--compact"])

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["gap"]["code"]
    assert payload["readiness"]["first_gap"] == payload["gap"]["code"]
    assert payload["root"] == str(tmp_path.resolve())
    assert payload["claim_boundary"]


def test_self_dna_current_map_keeps_execution_not_run_and_rejects_broken_bindings(tmp_path: Path) -> None:
    """Static map validity must not become a cached model/test PASS."""
    from physicsguard.self_dna import check
    from flowguard.map.mapfile import fingerprint, save_map

    (tmp_path / 'tests').mkdir()
    (tmp_path / '.flowguard/models').mkdir(parents=True)
    source = tmp_path / 'unit.py'
    test = tmp_path / 'tests/test_unit.py'
    model = tmp_path / '.flowguard/models/unit.py'
    source.write_text('def calculate():\n    return 1\n')
    test.write_text('def test_calculate():\n    assert True\n')
    model.write_text('MODEL_ID = "unit"\nCOMPONENTS = ["unit"]\nIMPLEMENTED_BY = {"calculate": "unit.py:calculate"}\nTESTED_BY = {"result": ["tests/test_unit.py:test_calculate"]}\ndef build_explorer():\n    raise AssertionError("static inspection must not execute models")\n')
    data = {'schema': 'flowguard.map.v1', 'project': 'unit', 'layers': [], 'ignore': [],
            'components': [{'id': 'unit', 'summary': 'Calculate a bounded value', 'responsibilities': ['Calculate'],
                            'files': ['unit.py'], 'tests': ['tests/test_unit.py'], 'models': ['.flowguard/models/unit.py'],
                            'status': 'confirmed', 'fingerprint': fingerprint(tmp_path, ['unit.py'])}], 'flows': []}
    save_map(tmp_path, data)
    initial, code = check(tmp_path)
    assert code == 0
    assert initial['model_execution'] == initial['test_execution'] == 'not_run'
    source.write_text('def calculate():\n    return 2\n')
    stale, code = check(tmp_path)
    assert code == 1 and any(row['code'] == 'stale' for row in stale['findings'])
    source.write_text('def calculate():\n    return 1\n')
    test.write_text('def test_calculate():\n    assert 1 == 1\n')
    changed, code = check(tmp_path)
    assert code == 0 and changed['components'][0]['test_fingerprint'] != initial['components'][0]['test_fingerprint']
    assert changed['test_execution'] == 'not_run'
    test.write_text('def test_renamed():\n    assert True\n')
    broken, code = check(tmp_path)
    assert code == 1 and any(row['code'] == 'model_test_broken' for row in broken['findings'])
    test.write_text('def test_calculate():\n    assert True\n')
    model.write_text(model.read_text() + '# revised model body\n')
    changed, code = check(tmp_path)
    assert code == 0 and changed['components'][0]['model_fingerprint'] != initial['components'][0]['model_fingerprint']
    assert changed['model_execution'] == 'not_run'
    model.unlink()
    missing, code = check(tmp_path)
    assert code == 1 and any(row['code'] == 'model_missing' for row in missing['findings'])
