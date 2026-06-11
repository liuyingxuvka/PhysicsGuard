from __future__ import annotations

from pathlib import Path

from physicsguard.core.dataset_identity import (
    check_logical_dataset_record,
    check_test_file_relation_index,
)


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def test_logical_dataset_record_passes_without_moving_raw_data() -> None:
    report = check_logical_dataset_record(PUMP / "datasets" / "clean_logical_dataset.yaml")

    assert report.ok
    assert report.summary["raw_data_policy"]["do_not_move_raw_data"] is True


def test_relation_index_is_symmetric_metadata_not_parent_contract() -> None:
    report = check_test_file_relation_index(PUMP / "relation_index.yaml")

    assert report.ok
    assert "do not make one contract a parent" in report.summary["semantics"]
