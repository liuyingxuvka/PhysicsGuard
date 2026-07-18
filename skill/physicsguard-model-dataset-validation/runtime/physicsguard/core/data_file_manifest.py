"""Generated manifest support for testbench data files."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Optional

from physicsguard.schema.data_file_manifest import (
    DataFileManifestSpec,
    DataFormatSpec,
    DataShapeSpec,
    ExtractorEvidenceSpec,
    FieldSummarySpec,
    SourceFileSpec,
    TimeBasisSpec,
)
from physicsguard.schema.test_file_contract import ExtractorProfileSpec, TestBenchProfileSpec


def sha256_file(path: str | Path) -> str:
    """Return a SHA-256 content hash for a local file."""

    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def field_signature_hash(manifest: DataFileManifestSpec) -> str:
    """Hash only field identity facts that should trigger schema-drift review."""

    signature = [
        {
            "name": field.name,
            "data_type": field.data_type,
            "unit": field.unit,
        }
        for field in manifest.fields
    ]
    return stable_json_hash(signature)


def generate_delimited_manifest(
    data_file: str | Path,
    *,
    profile: TestBenchProfileSpec | ExtractorProfileSpec | None = None,
    delimiter: str | None = None,
    encoding: str | None = None,
    time_column: str | None = None,
    manifest_id: str | None = None,
) -> DataFileManifestSpec:
    """Generate a lightweight CSV/TSV manifest without external dependencies."""

    file_path = Path(data_file)
    if not file_path.exists():
        raise FileNotFoundError(f"test data file not found: {file_path}")
    resolved_encoding = encoding or getattr(profile, "encoding", None) or "utf-8"
    resolved_delimiter = (
        delimiter
        or getattr(profile, "delimiter", None)
        or ("\t" if file_path.suffix.lower() in {".tsv", ".tab"} else ",")
    )
    resolved_time_column = time_column or getattr(profile, "time_column", None)
    field_units = dict(getattr(profile, "field_units", {}) or {})

    with file_path.open("r", encoding=resolved_encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=resolved_delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"test data file has no header row: {file_path}")
        fields = [name.strip() if name is not None else "" for name in reader.fieldnames]
        if any(not name for name in fields):
            raise ValueError("test data file header contains an empty field name")
        if len(fields) != len(set(fields)):
            raise ValueError("test data file header contains duplicate field names")
        rows = [dict(row) for row in reader]

    if resolved_time_column is None:
        resolved_time_column = _choose_time_column(fields)

    field_summaries = [
        _field_summary(field_name, [row.get(field_name, "") for row in rows], field_units.get(field_name))
        for field_name in fields
    ]
    time_basis = _time_basis(
        resolved_time_column,
        [row.get(resolved_time_column, "") for row in rows] if resolved_time_column else [],
        len(rows),
    )
    source_file = SourceFileSpec(
        path=str(file_path),
        content_hash=sha256_file(file_path),
        size_bytes=file_path.stat().st_size,
    )
    manifest = DataFileManifestSpec(
        manifest_id=manifest_id or file_path.stem,
        source_file=source_file,
        format=DataFormatSpec(
            kind="tsv" if resolved_delimiter == "\t" else "csv",
            delimiter=resolved_delimiter,
            encoding=resolved_encoding,
            header_rows=1,
        ),
        shape=DataShapeSpec(
            field_count=len(fields),
            row_count=len(rows),
            sample_count=len(rows),
        ),
        time=time_basis,
        fields=field_summaries,
        extractor=ExtractorEvidenceSpec(
            script="physicsguard.core.data_file_manifest.generate_delimited_manifest",
            script_hash=_self_script_hash(),
            generated_at=datetime.now(timezone.utc).isoformat(),
            version="1",
        ),
    )
    return manifest.model_copy(update={"field_signature_hash": field_signature_hash(manifest)})


def manifest_to_dict(manifest: DataFileManifestSpec) -> dict[str, Any]:
    return manifest.model_dump(mode="json", exclude_none=True)


def _field_summary(field_name: str, values: Iterable[str | None], unit: str | None) -> FieldSummarySpec:
    non_null = 0
    null = 0
    observed_types: list[str] = []
    numeric_values: list[float] = []
    for raw in values:
        value = "" if raw is None else str(raw).strip()
        if value == "":
            null += 1
            continue
        non_null += 1
        value_type = _infer_scalar_type(value)
        observed_types.append(value_type)
        if value_type in {"integer", "float"}:
            numeric_values.append(float(value))
    data_type = _merge_types(observed_types)
    min_value = min(numeric_values) if numeric_values and data_type in {"integer", "float"} else None
    max_value = max(numeric_values) if numeric_values and data_type in {"integer", "float"} else None
    return FieldSummarySpec(
        name=field_name,
        data_type=data_type,
        unit=unit,
        non_null_count=non_null,
        null_count=null,
        min_value=min_value,
        max_value=max_value,
    )


def _infer_scalar_type(value: str) -> str:
    lowered = value.lower()
    if lowered in {"true", "false", "yes", "no", "on", "off"}:
        return "boolean"
    try:
        int(value)
    except ValueError:
        pass
    else:
        return "integer"
    try:
        float(value)
    except ValueError:
        return "string"
    return "float"


def _merge_types(types: list[str]) -> str:
    if not types:
        return "empty"
    unique = set(types)
    if unique == {"integer"}:
        return "integer"
    if unique <= {"integer", "float"}:
        return "float" if "float" in unique else "integer"
    if len(unique) == 1:
        return types[0]
    return "mixed"


def _choose_time_column(fields: list[str]) -> Optional[str]:
    lowered = {field.lower(): field for field in fields}
    for candidate in ("time", "timestamp", "timestamp_s", "t_s", "seconds", "sec"):
        if candidate in lowered:
            return lowered[candidate]
    return None


def _time_basis(time_column: str | None, values: list[str | None], row_count: int) -> TimeBasisSpec:
    if time_column is None:
        return TimeBasisSpec(
            sampling_mode="snapshot" if row_count <= 1 else "unknown",
            continuity="not_applicable" if row_count <= 1 else "unknown",
        )
    parsed: list[tuple[str, float]] = []
    for raw in values:
        value = "" if raw is None else str(raw).strip()
        if value == "":
            continue
        seconds = _parse_time_seconds(value)
        if seconds is not None:
            parsed.append((value, seconds))
    if not parsed:
        return TimeBasisSpec(
            time_column=time_column,
            sampling_mode="time_series",
            continuity="unknown",
        )
    start_raw, start_s = parsed[0]
    end_raw, end_s = parsed[-1]
    duration = max(0.0, end_s - start_s)
    sample_rate = (len(parsed) - 1) / duration if duration > 0 and len(parsed) > 1 else None
    continuity, gap_count = _continuity([seconds for _raw, seconds in parsed])
    return TimeBasisSpec(
        time_column=time_column,
        start_time=_typed_time_value(start_raw),
        end_time=_typed_time_value(end_raw),
        duration_s=duration,
        nominal_sample_rate_hz=sample_rate,
        sampling_mode="time_series",
        continuity=continuity,
        gap_count=gap_count,
    )


def _parse_time_seconds(value: str) -> Optional[float]:
    try:
        return float(value)
    except ValueError:
        pass
    iso_value = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _typed_time_value(value: str) -> str | float:
    try:
        return float(value)
    except ValueError:
        return value


def _continuity(seconds: list[float]) -> tuple[str, int]:
    if len(seconds) <= 1:
        return "not_applicable", 0
    deltas = [b - a for a, b in zip(seconds, seconds[1:])]
    if any(delta < 0 for delta in deltas):
        return "irregular", sum(1 for delta in deltas if delta < 0)
    positive = [delta for delta in deltas if delta > 0]
    if not positive:
        return "irregular", len(deltas)
    nominal = median(positive)
    if nominal <= 0:
        return "irregular", len(deltas)
    gaps = [delta for delta in positive if delta > nominal * 1.5]
    if gaps:
        return "continuous_with_gaps", len(gaps)
    return "continuous", 0


def _self_script_hash() -> str:
    return sha256_file(Path(__file__))


__all__ = [
    "field_signature_hash",
    "generate_delimited_manifest",
    "manifest_to_dict",
    "sha256_file",
    "stable_json_hash",
]
