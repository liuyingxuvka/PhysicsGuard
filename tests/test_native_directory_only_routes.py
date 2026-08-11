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


def test_self_dna_export_route_is_typed_native_directory_only(tmp_path: Path, capsys) -> None:
    output = tmp_path / "self-dna.json"
    code = main(
        [
            "self-dna",
            "export",
            "--root",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["gap"]["code"] == "native_directory_only"
    assert payload["native_directory_only"]["kind"] == "native_directory_only"
    assert not output.exists()


def test_compact_self_dna_preserves_first_gap_and_boundary(tmp_path: Path, capsys) -> None:
    code = main(["self-dna", "check", "--root", str(tmp_path), "--compact"])

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["gap"]["code"]
    assert payload["readiness"]["first_gap"] == payload["gap"]["code"]
    assert payload["root"] == str(tmp_path.resolve())
    assert payload["claim_boundary"]
