from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.model_library import check_model_library_index
from physicsguard.schema.model_library import ModelLibraryEntrySpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def test_model_library_index_passes_with_validation_reference() -> None:
    report = check_model_library_index(PUMP / "model_library.yaml")

    assert report.ok
    assert report.summary["entry_count"] == 1


def test_validated_library_entry_requires_validation_report() -> None:
    with pytest.raises(ValueError):
        ModelLibraryEntrySpec.model_validate(
            {
                "model_id": "bad",
                "model_file": "model.yaml",
                "reuse_status": "validated",
            }
        )
