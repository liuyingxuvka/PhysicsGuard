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
