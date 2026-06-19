from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import RAW_DATA_POLICY, closure_result, dump_json, load_struct, utc_now, write_json


ROOT_DIRECTORIES = (
    "contracts",
    "projects",
    "provider_results",
    "navigation",
    "closure_reports",
    "queries",
)

ROOT_FILES = (
    "DATABASE_README.md",
    "DATABASE_STATUS.md",
    "databank_policy.json",
    "database_catalog.json",
    "database_history.jsonl",
)


def _default_policy(database_id: str) -> dict[str, Any]:
    return {
        "database_id": database_id,
        "schema": "databank-root-v1",
        "created_at": utc_now(),
        "raw_data_policy": RAW_DATA_POLICY,
        "require_provider_closure": True,
        "require_history_events": True,
        "allowed_lifecycle_states": [
            "candidate",
            "placeholder",
            "active_registered",
            "active_validated",
            "active_reusable",
            "blocked",
            "downgraded",
            "archived",
            "deprecated",
            "superseded",
            "rejected",
        ],
    }


def _default_catalog(database_id: str) -> dict[str, Any]:
    return {
        "database_id": database_id,
        "schema": "databank-catalog-v1",
        "projects": [],
        "records": [],
    }


def _write_default_files(root: Path, database_id: str) -> None:
    (root / "DATABASE_README.md").write_text(
        "\n".join(
            [
                f"# DataBank Database: {database_id}",
                "",
                "Read DATABASE_STATUS.md, databank_policy.json, database_catalog.json,",
                "provider_results/, contracts/, navigation/, and closure_reports/ before",
                "making database-level claims.",
                "",
                RAW_DATA_POLICY,
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "DATABASE_STATUS.md").write_text(
        "\n".join(
            [
                f"# DataBank Status: {database_id}",
                "",
                "- status: candidate",
                "- safe_claim: Database root exists; project evidence still requires provider closure.",
                "- unsafe_claim_boundary: Do not claim validated or reusable until closure reports pass.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    dump_json(_default_policy(database_id), root / "databank_policy.json")
    dump_json(_default_catalog(database_id), root / "database_catalog.json")
    history = root / "database_history.jsonl"
    if not history.exists():
        history.write_text("", encoding="utf-8")


def check_root(root_path: str | Path, *, init: bool = False, database_id: str | None = None) -> dict[str, Any]:
    root = Path(root_path).resolve()
    db_id = database_id or root.name or "databank"
    created: list[str] = []
    missing_inputs: list[Any] = []
    evidence: list[Any] = []

    if init:
        root.mkdir(parents=True, exist_ok=True)
        for directory in ROOT_DIRECTORIES:
            path = root / directory
            if not path.exists():
                path.mkdir(parents=True)
                created.append(str(path))
        for file_name in ROOT_FILES:
            if not (root / file_name).exists():
                if file_name in {"DATABASE_README.md", "DATABASE_STATUS.md", "databank_policy.json", "database_catalog.json", "database_history.jsonl"}:
                    continue
                (root / file_name).touch()
        _write_default_files(root, db_id)

    if not root.exists() or not root.is_dir():
        return closure_result(
            "blocked",
            missing_inputs=[{"id": "database_root", "path": str(root), "reason": "missing_or_not_directory"}],
            unsafe_claim_boundary="Cannot audit or use a missing DataBank root.",
            next_actions=["Create an explicit database root with --init."],
        )

    for directory in ROOT_DIRECTORIES:
        path = root / directory
        if path.is_dir():
            evidence.append({"id": f"dir:{directory}", "path": str(path)})
        else:
            missing_inputs.append({"id": f"dir:{directory}", "path": str(path), "reason": "missing_directory"})

    for file_name in ROOT_FILES:
        path = root / file_name
        if path.is_file():
            evidence.append({"id": f"file:{file_name}", "path": str(path)})
        else:
            missing_inputs.append({"id": f"file:{file_name}", "path": str(path), "reason": "missing_file"})

    parse_errors: list[Any] = []
    for file_name in ("databank_policy.json", "database_catalog.json"):
        path = root / file_name
        if path.exists():
            try:
                load_struct(path)
            except Exception as exc:
                parse_errors.append({"id": file_name, "path": str(path), "reason": str(exc)})

    if parse_errors:
        missing_inputs.extend(parse_errors)

    status = "blocked" if missing_inputs else "pass"
    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=missing_inputs,
        safe_claim="DataBank root layout is present and parseable." if status == "pass" else "",
        unsafe_claim_boundary="" if status == "pass" else "Do not use this folder as a complete DataBank root yet.",
        next_actions=["Create missing root files/directories or rerun with --init."] if status != "pass" else [],
        extra={"created": created, "root": str(root), "database_id": db_id},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or initialize a DataBank root layout.")
    parser.add_argument("database_root", help="Explicit DataBank root")
    parser.add_argument("--init", action="store_true", help="Create missing root files and directories")
    parser.add_argument("--database-id", help="Stable database id for initialized metadata")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = check_root(args.database_root, init=args.init, database_id=args.database_id)
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
