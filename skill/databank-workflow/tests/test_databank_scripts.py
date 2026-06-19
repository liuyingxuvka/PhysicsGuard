from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
VALIDATOR = Path(r"C:\Users\liu_y\.codex\skills\.system\skill-creator\scripts\quick_validate.py")
VALID_SHA = "a" * 64


def run_script(script_name: str, *args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"{script_name} did not emit JSON\nstdout={completed.stdout}\nstderr={completed.stderr}"
        ) from exc
    return completed.returncode, payload


class DataBankScriptTests(unittest.TestCase):
    def test_skill_validate(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), str(SKILL_ROOT)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_nav_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.md").write_text("source", encoding="utf-8")
            manifest = root / "nav.json"
            manifest.write_text(
                json.dumps({"project_id": "p1", "source_files": [{"label": "source", "path": "source.md"}]}),
                encoding="utf-8",
            )
            code, payload = run_script("databank_nav_render.py", str(manifest), "--output", str(root / "PROJECT_NAV_INDEX.md"))
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "pass")
            self.assertTrue((root / "PROJECT_NAV_INDEX.md").exists())

            manifest.write_text(
                json.dumps({"project_id": "p1", "source_files": [{"label": "missing", "path": "missing.md"}]}),
                encoding="utf-8",
            )
            code, payload = run_script("databank_nav_render.py", str(manifest))
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertTrue(payload["missing_inputs"])

    def test_freshness_detects_hash_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "freshness.json"
            manifest.write_text(
                json.dumps(
                    {
                        "current_hashes": {"model_hash": "new-model", "contract_hash": "same-contract"},
                        "validation_reports": [
                            {"id": "report", "model_hash": "old-model", "contract_hash": "same-contract"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script("databank_freshness_check.py", str(manifest))
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["stale_evidence"][0]["reason"], "validation_report_references_stale_hash")

    def test_catalog_cannot_hide_blocked_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = root / "provider.json"
            catalog = root / "catalog.json"
            provider.write_text(
                json.dumps(
                    {
                        "id": "physicsguard",
                        "status": "blocked",
                        "evidence": [],
                        "missing_inputs": [{"id": "contract", "reason": "model_hash_mismatch"}],
                        "stale_evidence": [],
                        "skipped_checks": [],
                        "safe_claim": "",
                        "unsafe_claim_boundary": "blocked",
                        "next_actions": ["refresh contract"],
                    }
                ),
                encoding="utf-8",
            )
            catalog.write_text(
                json.dumps({"projects": [{"id": "p1", "lifecycle_state": "active_validated"}]}),
                encoding="utf-8",
            )
            code, payload = run_script("databank_closure_check.py", "--provider", str(provider), "--catalog", str(catalog))
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "downgraded")
            self.assertTrue(payload["catalog_conflicts"])

    def test_project_intake_no_raw_data_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            database = root / "database"
            project.mkdir()
            database.mkdir()
            (project / "measurements.csv").write_text("time,value\n0,1\n", encoding="utf-8")
            output = database / "registry.json"
            code, payload = run_script(
                "databank_intake.py",
                str(project),
                "--database",
                str(database),
                "--project-id",
                "p1",
                "--output",
                str(output),
            )
            self.assertEqual(code, 0)
            self.assertFalse(payload["registry"]["copied_raw_data"])
            self.assertTrue(payload["registry"]["data_manifest"])
            self.assertFalse((database / "measurements.csv").exists())

    def test_query_gate_outputs_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Path(tmp) / "catalog.json"
            catalog.write_text(json.dumps({"projects": [{"id": "p1", "tags": ["fuel-cell"]}]}), encoding="utf-8")
            code, payload = run_script("databank_query.py", str(catalog), "--field", "id", "--value", "missing")
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "partial")
            self.assertEqual(payload["matches"], [])
            self.assertIn("No records matched", payload["reason"])

    def test_provider_contract_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "bad_provider.json"
            provider.write_text(json.dumps({"id": "logicguard", "status": "pass"}), encoding="utf-8")
            code, payload = run_script("databank_closure_check.py", "--provider", str(provider))
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertTrue(payload["missing_inputs"][0]["missing_fields"])

    def test_contract_check_requires_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contracts = Path(tmp) / "contracts.json"
            contracts.write_text(
                json.dumps({"contracts": [{"contract_type": "source", "id": "s1", "path": "report.pdf"}]}),
                encoding="utf-8",
            )
            code, payload = run_script("databank_contract_check.py", str(contracts))
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertIn("sha256", payload["missing_inputs"][0]["missing_fields"])

            contracts.write_text(
                json.dumps(
                    {
                        "contracts": [
                            {
                                "contract_type": "query",
                                "query": {"field": "id", "value": "p1"},
                                "scope": {"records_inspected": 1},
                                "matches": [],
                                "reason": "No records matched id='p1'.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script("databank_contract_check.py", str(contracts))
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "pass")

    def test_contract_check_rejects_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contracts = Path(tmp) / "contracts.json"
            contracts.write_text(
                json.dumps(
                    {
                        "contracts": [
                            {
                                "contract_type": "source",
                                "id": "s1",
                                "path": "missing.md",
                                "sha256": "not-a-sha",
                                "source_type": "report",
                                "read_only": True,
                                "provenance": "fixture",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script("databank_contract_check.py", str(contracts), "--check-paths", "--base", tmp)
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")
            invalid = payload["missing_inputs"][0]["invalid_fields"]
            self.assertTrue(any(item["reason"] == "invalid_sha256" for item in invalid))
            self.assertTrue(any(item["reason"] == "path_missing" for item in invalid))

            contracts.write_text(
                json.dumps(
                    {
                        "contracts": [
                            {
                                "contract_type": "closure",
                                "status": "pass",
                                "evidence": [],
                                "missing_inputs": [],
                                "stale_evidence": [],
                                "skipped_checks": [],
                                "safe_claim": "unsafe empty evidence",
                                "unsafe_claim_boundary": "",
                                "next_actions": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script("databank_contract_check.py", str(contracts))
            self.assertNotEqual(code, 0)
            self.assertTrue(
                any(item["reason"] == "pass_requires_evidence" for item in payload["missing_inputs"][0]["invalid_fields"])
            )

    def test_root_init_and_audit_pass_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "db"
            code, payload = run_script("databank_root_check.py", str(root), "--init", "--database-id", "fixture_db")
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "pass")
            self.assertTrue((root / "DATABASE_README.md").exists())
            self.assertTrue((root / "contracts").is_dir())

            source = root / "projects" / "p1" / "source.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("source evidence\n", encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            contracts = root / "contracts" / "source.json"
            contracts.write_text(
                json.dumps(
                    {
                        "contracts": [
                            {
                                "contract_type": "source",
                                "id": "source-1",
                                "path": "projects/p1/source.md",
                                "sha256": digest,
                                "source_type": "report",
                                "read_only": True,
                                "provenance": "fixture",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            provider = root / "provider_results" / "physicsguard.json"
            provider.write_text(
                json.dumps(
                    {
                        "id": "physicsguard",
                        "status": "pass",
                        "evidence": [{"id": "project-closure"}],
                        "missing_inputs": [],
                        "stale_evidence": [],
                        "skipped_checks": [],
                        "safe_claim": "fixture provider passed",
                        "unsafe_claim_boundary": "",
                        "next_actions": [],
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script("databank_audit.py", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["status"], "pass")
            self.assertTrue(any(section["name"] == "closure" for section in payload["sections"]))

    def test_provider_adapter_blocks_provider_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "physicsguard_report.json"
            provider.write_text(
                json.dumps(
                    {
                        "artifact_kind": "database_maintenance_report",
                        "status": "pass",
                        "blocking_gaps": [{"id": "registry", "reason": "missing"}],
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script("databank_provider_adapter.py", str(provider), "--provider", "physicsguard")
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertTrue(payload["missing_inputs"])

    def test_lifecycle_requires_closure_for_validated_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "db"
            run_script("databank_root_check.py", str(root), "--init", "--database-id", "fixture_db")
            code, payload = run_script(
                "databank_lifecycle.py",
                str(root),
                "p1",
                "--state",
                "active_validated",
                "--reason",
                "not enough evidence",
            )
            self.assertNotEqual(code, 0)
            self.assertEqual(payload["status"], "blocked")

            closure = root / "closure_reports" / "p1.json"
            closure.write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "evidence": [{"id": "provider-closure"}],
                        "missing_inputs": [],
                        "stale_evidence": [],
                        "skipped_checks": [],
                        "safe_claim": "validated fixture",
                        "unsafe_claim_boundary": "",
                        "next_actions": [],
                    }
                ),
                encoding="utf-8",
            )
            code, payload = run_script(
                "databank_lifecycle.py",
                str(root),
                "p1",
                "--state",
                "active_registered",
                "--reason",
                "registered fixture",
                "--apply",
            )
            self.assertEqual(code, 0, payload)
            code, payload = run_script(
                "databank_lifecycle.py",
                str(root),
                "p1",
                "--state",
                "active_validated",
                "--reason",
                "provider closure passed",
                "--closure",
                str(closure),
                "--apply",
            )
            self.assertEqual(code, 0, payload)
            catalog = json.loads((root / "database_catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["projects"][0]["lifecycle_state"], "active_validated")
            self.assertTrue((root / "database_history.jsonl").read_text(encoding="utf-8").strip())

    def test_physicsguard_database_catalog_routes_total_ledger_to_databank(self) -> None:
        catalog_skill = Path(r"C:\Users\liu_y\.codex\skills\physicsguard-database-catalog\SKILL.md")
        text = catalog_skill.read_text(encoding="utf-8")
        self.assertIn("route to `databank-workflow`", text)
        self.assertNotIn("route to\n`physicsguard-database-adoption`", text)
        self.assertNotIn("route to `physicsguard-database-project-intake`", text)

    def test_non_database_physicsguard_skills_do_not_route_to_legacy_database_skills(self) -> None:
        skills_root = Path(r"C:\Users\liu_y\.codex\skills")
        offenders = []
        for skill_dir in skills_root.glob("physicsguard-*"):
            if not skill_dir.is_dir() or skill_dir.name.startswith("physicsguard-database-"):
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists() and "physicsguard-database-" in skill_file.read_text(encoding="utf-8"):
                offenders.append(str(skill_file))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
