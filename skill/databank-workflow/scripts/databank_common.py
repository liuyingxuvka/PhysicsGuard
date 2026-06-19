from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLOSURE_STATUSES = {"pass", "partial", "blocked", "downgraded"}

BROAD_CLAIMS = {
    "pass",
    "validated",
    "fully_validated",
    "active_validated",
    "active_reusable",
    "reusable",
}

LIFECYCLE_STATES = {
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
}

ACTIVE_BROAD_STATES = {"active_validated", "active_reusable"}
TERMINAL_LIFECYCLE_STATES = {"archived", "deprecated", "superseded", "rejected"}

REQUIRED_CLOSURE_KEYS = {
    "status",
    "evidence",
    "missing_inputs",
    "stale_evidence",
    "skipped_checks",
    "safe_claim",
    "unsafe_claim_boundary",
    "next_actions",
}

RAW_DATA_POLICY = (
    "Large raw datasets stay in source locations; DataBank stores only paths, "
    "hashes, summaries, and evidence references."
)


def load_struct(path: str | Path) -> Any:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on environment
            raise ValueError("YAML input requires PyYAML; use JSON instead") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def dump_json(data: Any, path: str | Path, *, pretty: bool = True) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if pretty else None
    output.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def write_json(data: Any, *, pretty: bool = False) -> None:
    indent = 2 if pretty else None
    print(json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=pretty))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_dict_records(value: Any) -> list[dict[str, Any]]:
    return [item for item in as_list(value) if isinstance(item, dict)]


def get_path(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def normalize_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    if value in {"pass", "passed", "ok", "green", "validated"}:
        return "pass"
    if value in {"partial", "warning", "degraded"}:
        return "partial"
    if value in {"downgraded"}:
        return "downgraded"
    return "blocked"


def normalize_lifecycle_state(state: Any) -> str:
    value = str(state or "").strip().lower()
    return value if value in LIFECYCLE_STATES else "blocked"


def is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def is_sha256_hex(value: Any) -> bool:
    text = str(value or "")
    if len(text) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in text)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_path(base: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(base) / path


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{file_path}:{line_number} is not valid JSONL") from exc
        if isinstance(item, dict):
            rows.append(item)
    return rows


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def closure_result(
    status: str,
    *,
    evidence: list[Any] | None = None,
    missing_inputs: list[Any] | None = None,
    stale_evidence: list[Any] | None = None,
    skipped_checks: list[Any] | None = None,
    safe_claim: str = "",
    unsafe_claim_boundary: str = "",
    next_actions: list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "evidence": evidence or [],
        "missing_inputs": missing_inputs or [],
        "stale_evidence": stale_evidence or [],
        "skipped_checks": skipped_checks or [],
        "safe_claim": safe_claim,
        "unsafe_claim_boundary": unsafe_claim_boundary,
        "next_actions": next_actions or [],
    }
    if extra:
        result.update(extra)
    return result


def is_raw_data_candidate(path: Path) -> bool:
    raw_suffixes = {
        ".csv",
        ".tsv",
        ".parquet",
        ".h5",
        ".hdf5",
        ".mat",
        ".mf4",
        ".dat",
        ".bin",
        ".xlsx",
        ".xls",
    }
    return path.suffix.lower() in raw_suffixes
