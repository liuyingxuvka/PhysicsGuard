from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from physicsguard.core.database_catalog import (
    build_database_map,
    check_database_catalog,
    check_database_catalog_gaps,
    query_database_catalog,
    refresh_database_catalog,
    scan_database_catalog_candidates,
)
from physicsguard.schema.database_catalog import (
    DatabaseCatalogGapReportSpec,
    DatabaseCatalogSpec,
    DatabaseMapReportSpec,
    DatabaseQueryReportSpec,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "examples" / "database_catalog" / "database_catalog.yaml"
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def test_database_catalog_check_gap_map_and_query_pass() -> None:
    review = check_database_catalog(CATALOG)
    gap_report = check_database_catalog_gaps(CATALOG)
    database_map = build_database_map(CATALOG)
    query = query_database_catalog(CATALOG, quantity="pump.flow_readback")

    assert review.ok
    assert gap_report.ok
    assert database_map.ok
    assert query.ok
    assert database_map.summary["project_count"] == 1
    assert database_map.summary["project_with_registry_count"] == 1
    assert "pump.flow_readback" in database_map.indexes["quantities"]
    assert query.summary["match_count"] == 1
    assert query.matches[0]["project_id"] == "pump_loop_fixture_project"
    assert DatabaseCatalogGapReportSpec.model_validate(gap_report.to_dict()).status == "pass"
    assert DatabaseMapReportSpec.model_validate(database_map.to_dict()).status == "pass"
    assert DatabaseQueryReportSpec.model_validate(query.to_dict()).status == "pass"


def test_database_catalog_refresh_reads_project_registry() -> None:
    report = refresh_database_catalog(CATALOG)

    assert report.ok
    assert report.summary["refreshed_project_count"] == 1
    project = report.refreshed_projects[0]
    assert project["registry_loaded"] is True
    assert project["has_test_data"] is True
    assert "pump_signal_map.x" in project["model_targets"]
    assert "pump.commanded_speed" in project["tested_quantities"]


def test_database_catalog_scan_marks_registered_project_and_library() -> None:
    report = scan_database_catalog_candidates(PUMP, CATALOG)

    assert report.ok
    registered = [item for item in report.candidates if item["registered"]]
    assert any(item["candidate_kind"] == "project_evidence_registry" for item in registered)
    assert any(item["candidate_kind"] == "model_library" for item in registered)
    assert report.summary["candidate_count"] >= 2


def test_missing_project_registry_reports_blocking_gap(tmp_path: Path) -> None:
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    data["projects"][0]["project_evidence_registry"] = "missing/project_evidence_registry.yaml"
    catalog = tmp_path / "missing_registry_catalog.yaml"
    catalog.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    report = check_database_catalog_gaps(catalog)

    assert not report.ok
    assert any(gap["gap_type"] == "project_registry_path_missing" for gap in report.blocking_gaps)


def test_project_registry_blocking_gap_propagates_to_database(tmp_path: Path) -> None:
    registry_data = yaml.safe_load((PUMP / "evidence" / "project_evidence_registry.yaml").read_text(encoding="utf-8"))
    registry_data["evidence_bindings"] = [
        item for item in registry_data["evidence_bindings"] if item["binding_id"] != "clean_flow_readback_to_model_y"
    ]
    registry_data["evidence_bundles"][0]["bindings"] = [
        item for item in registry_data["evidence_bundles"][0]["bindings"] if item != "clean_flow_readback_to_model_y"
    ]
    registry = tmp_path / "project_evidence_registry.yaml"
    registry.write_text(yaml.safe_dump(registry_data, sort_keys=False), encoding="utf-8")
    catalog_data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    catalog_data["projects"][0]["project_evidence_registry"] = str(registry)
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(yaml.safe_dump(catalog_data, sort_keys=False), encoding="utf-8")

    report = check_database_catalog_gaps(catalog)

    assert not report.ok
    assert any(gap["gap_type"] == "project_binding_expectation_unmet" for gap in report.blocking_gaps)
    assert any(gap["project_id"] == "pump_loop_fixture_project" for gap in report.blocking_gaps)


def test_raw_data_payload_in_catalog_metadata_is_blocking(tmp_path: Path) -> None:
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    data["metadata"] = {"raw_data": [{"time_s": 0.0, "value": 1.0}]}
    catalog = tmp_path / "raw_payload_catalog.yaml"
    catalog.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    review = check_database_catalog(catalog)
    gaps = check_database_catalog_gaps(catalog)

    assert not review.ok
    assert not gaps.ok
    assert any(gap["gap_type"] == "catalog_raw_data_payload" for gap in gaps.blocking_gaps)


def test_duplicate_project_ids_fail_schema() -> None:
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    data["projects"].append(dict(data["projects"][0]))

    with pytest.raises(ValueError, match="project ids must be unique"):
        DatabaseCatalogSpec.model_validate(data)


def test_database_cli_commands() -> None:
    commands = [
        ["database", "check", str(CATALOG), "--pretty"],
        ["database", "gap-check", str(CATALOG), "--pretty"],
        ["database", "map", str(CATALOG), "--pretty"],
        ["database", "query", str(CATALOG), "--quantity", "pump.commanded_speed", "--pretty"],
    ]
    for command in commands:
        result = subprocess.run(
            [sys.executable, "-m", "physicsguard.cli", *command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
