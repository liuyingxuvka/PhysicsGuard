from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import closure_result, load_struct, write_json


SECTION_ORDER = [
    ("source_files", "Source Files"),
    ("test_data", "Test Data"),
    ("models", "Models"),
    ("validation", "Validation"),
    ("report_conclusions", "Report Conclusions"),
    ("timeline", "Timeline"),
    ("queries", "Queries"),
]


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _entry_label(entry: dict[str, Any]) -> str:
    return str(entry.get("label") or entry.get("id") or entry.get("path") or "item")


def render_nav(manifest_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_struct(manifest_file)
    base = manifest_file.parent
    project = manifest.get("project_id") or manifest.get("name") or "project"
    lines = [f"# PROJECT_NAV_INDEX: {project}", ""]
    broken_links: list[Any] = []
    evidence: list[Any] = []

    for key, title in SECTION_ORDER:
        lines.extend([f"## {title}", ""])
        entries = manifest.get(key, [])
        if not entries:
            lines.extend(["- No entries recorded.", ""])
            continue
        for entry in entries:
            if isinstance(entry, str):
                entry = {"path": entry}
            label = _entry_label(entry)
            target = entry.get("path")
            note = entry.get("note", "")
            if target:
                resolved = _resolve(base, str(target))
                if not resolved.exists():
                    broken_links.append({"section": key, "label": label, "path": str(resolved)})
                evidence.append({"section": key, "label": label, "path": str(resolved)})
                suffix = f" - {note}" if note else ""
                lines.append(f"- [{label}]({target}){suffix}")
            else:
                lines.append(f"- {label}")
        lines.append("")

    rendered = "\n".join(lines).rstrip() + "\n"
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")

    status = "blocked" if broken_links else "pass"
    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=broken_links,
        safe_claim="Navigation links resolve for the checked manifest." if status == "pass" else "",
        unsafe_claim_boundary="" if status == "pass" else "Do not claim the navigation index is valid while links are broken.",
        next_actions=["Fix or remove broken navigation links."] if broken_links else [],
        extra={"rendered": rendered, "broken_links": broken_links},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render and validate DataBank project navigation.")
    parser.add_argument("manifest", help="Navigation manifest JSON/YAML")
    parser.add_argument("--output", help="Optional PROJECT_NAV_INDEX.md output path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = render_nav(args.manifest, args.output)
    write_json({k: v for k, v in result.items() if k != "rendered"}, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
