from __future__ import annotations

from pathlib import Path

from physicsguard.io.test_file_contract_loader import (
    load_data_file_manifest,
    load_test_file_contract,
)
from physicsguard.schema.parameter_coverage import MappingEvidenceSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def test_generated_manifest_schema_records_file_shape_and_extractor() -> None:
    manifest = load_data_file_manifest(PUMP / "data" / "clean_manifest.yaml")

    assert manifest.shape.field_count == 4
    assert manifest.shape.row_count == 3
    assert manifest.time.time_column == "time_s"
    assert manifest.time.nominal_sample_rate_hz == 10.0
    assert manifest.extractor.script
    assert manifest.field_signature_hash


def test_test_file_contract_schema_allows_referenced_artifacts() -> None:
    contract = load_test_file_contract(PUMP / "contracts" / "clean_contract.yaml")

    assert contract.contract_id == "pump_loop_clean_contract"
    assert contract.manifest == "../data/clean_manifest.yaml"
    assert contract.mapping_edges == "../coverage/pump_loop_mapping_edges.yaml"


def test_mapping_evidence_schema_records_source_and_confidence() -> None:
    evidence = MappingEvidenceSpec(
        evidence_type="human_provided",
        source="test engineer",
        description="Engineer confirmed the field-to-variable mapping.",
        confidence=0.9,
    )

    assert evidence.evidence_type == "human_provided"
    assert evidence.confidence == 0.9
