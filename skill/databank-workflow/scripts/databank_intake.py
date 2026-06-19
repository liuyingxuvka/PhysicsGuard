from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import closure_result, is_raw_data_candidate, sha256_file, write_json


def intake(project_root: str | Path, database_root: str | Path, project_id: str | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    database = Path(database_root).resolve()
    if not root.exists() or not root.is_dir():
        return closure_result(
            "blocked",
            missing_inputs=[{"id": "project_root", "path": str(root), "reason": "missing_or_not_directory"}],
            unsafe_claim_boundary="Cannot intake a missing project root.",
            next_actions=["Provide a readable project root."],
        )

    records: list[dict[str, Any]] = []
    raw_data_refs: list[dict[str, Any]] = []
    document_refs: list[dict[str, Any]] = []
    source_refs: list[dict[str, Any]] = []

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root).as_posix()
        record = {
            "path": str(path),
            "relative_path": rel,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "suffix": path.suffix.lower(),
            "raw_data_candidate": is_raw_data_candidate(path),
        }
        records.append(record)
        if record["raw_data_candidate"]:
            raw_data_refs.append(record)
        elif path.suffix.lower() in {".md", ".txt", ".pdf", ".docx", ".pptx"}:
            document_refs.append(record)
        else:
            source_refs.append(record)

    registry: dict[str, Any] = {
        "project_id": project_id or root.name,
        "project_root": str(root),
        "database_root": str(database),
        "copied_raw_data": False,
        "source_registry": source_refs,
        "document_registry": document_refs,
        "data_manifest": raw_data_refs,
        "all_files": records,
    }
    evidence = [{"id": "intake_registry", "file_count": len(records), "raw_data_ref_count": len(raw_data_refs)}]
    return closure_result(
        "pass",
        evidence=evidence,
        safe_claim="Project intake recorded metadata and did not copy raw data.",
        next_actions=["Review generated registries and run provider-specific contract checks."],
        extra={"registry": registry},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create metadata-only DataBank intake registry.")
    parser.add_argument("project_root", help="Project root to scan")
    parser.add_argument("--database", required=True, help="Database root for registry metadata")
    parser.add_argument("--project-id", help="Project id to store in the registry")
    parser.add_argument("--output", help="Optional registry JSON output path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = intake(args.project_root, args.database, args.project_id)
    if args.output and result["status"] == "pass":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        import json

        output.write_text(json.dumps(result["registry"], ensure_ascii=False, indent=2), encoding="utf-8")
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
