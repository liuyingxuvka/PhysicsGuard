"""Explicit FlowGuard-owned PhysicsGuard software self-DNA route.

The physical-model blueprint remains an external-object/domain model.  This
module audits the PhysicsGuard repository itself through FlowGuard's released
self-blueprint provider and never creates a parallel schema, disk bundle, or
reconstruction path.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
from typing import Any


REPORT_KIND = "physicsguard.flowguard_software_self_dna_report.v1"
LAYER_IDS = (
    "evidence_qualification",
    "implementation_inventory",
    "traceability",
    "independent_semantics",
    "model_code_test_binding",
    "resource_oracle_binding",
    "static_blueprint_readiness",
)


def _native_directory_only(root: Path) -> dict[str, Any]:
    """Describe the one canonical software-DNA authority and its hard boundary."""

    return {
        "kind": "native_directory_only",
        "status": "enforced",
        "canonical_root": str(root),
        "canonical_authority": "repository_native_flowguard_definition",
        "disk_export": "prohibited",
        "bundle_materialization": "prohibited",
        "alternate_head": "prohibited",
        "cache_authority": "prohibited",
    }


def _flowguard_identity() -> dict[str, str]:
    try:
        version = importlib.metadata.version("flowguard")
    except importlib.metadata.PackageNotFoundError:
        version = "unavailable"
    try:
        import flowguard

        return {
            "package": "flowguard",
            "version": version,
            "schema_version": str(flowguard.SCHEMA_VERSION),
            "module": str(Path(flowguard.__file__).resolve()),
        }
    except (ImportError, AttributeError) as exc:
        return {
            "package": "flowguard",
            "version": version,
            "schema_version": "unavailable",
            "module": "unavailable",
            "import_error": f"{type(exc).__name__}: {exc}",
        }


def _blocked(root: Path, code: str, message: str, *, exc: Exception | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "report_kind": REPORT_KIND,
        "software_id": "physicsguard",
        "target_kind": "software",
        "status": "blocked",
        "ok": False,
        "root": str(root),
        "native_directory_only": _native_directory_only(root),
        "claim_boundary": "Only the exact PhysicsGuard repository boundary is covered; the physical-object DNA route remains separate.",
        "flowguard": _flowguard_identity(),
        "readiness": {
            "layers": [
                {"layer": layer, "status": "blocked", "gap": code if index == 0 else ""}
                for index, layer in enumerate(LAYER_IDS)
            ],
            "deepest_proven_layer": "",
            "first_gap": code,
            "gap_count": 1,
        },
        "gap": {"code": code, "message": message},
        "dna_qualification": {
            "status": "blocked",
            "qualified": False,
            "reasons": [code],
        },
    }
    if exc is not None:
        result["gap"]["exception"] = f"{type(exc).__name__}: {exc}"
    return result


def _build(root: Path) -> tuple[dict[str, Any], Any | None]:
    try:
        from flowguard.self_blueprint import FlowGuardSelfBlueprintError, build_flowguard_self_blueprint
    except (ImportError, AttributeError) as exc:
        return _blocked(root, "flowguard_toolchain_unavailable", "The current FlowGuard self-blueprint API cannot be imported.", exc=exc), None
    try:
        bundle = build_flowguard_self_blueprint(root)
    except FlowGuardSelfBlueprintError as exc:
        return _blocked(root, "flowguard_self_blueprint_not_ready", "FlowGuard rejected the current PhysicsGuard project authority, definition, inventory, or model evidence; no local substitute is used.", exc=exc), None
    except (OSError, ValueError) as exc:
        return _blocked(root, "flowguard_self_blueprint_input_invalid", "The current FlowGuard self-blueprint inputs are invalid or unavailable.", exc=exc), None
    qualification = getattr(bundle, "dna_qualification", None)
    if qualification is None:
        return _blocked(
            root,
            "flowguard_dna_qualification_missing",
            "The current FlowGuard self-blueprint did not expose its provider-neutral DNA qualification contract.",
        ), None
    qualified = bool(qualification.qualified)
    return {
        "report_kind": REPORT_KIND,
        "software_id": "physicsguard",
        "target_kind": "software",
        "status": "ready" if bundle.ok and qualified else "not_ready",
        "ok": bool(bundle.ok and qualified),
        "root": str(root),
        "native_directory_only": _native_directory_only(root),
        "claim_boundary": "This is the FlowGuard repository software-DNA boundary. PhysicsGuard's physical-model blueprint is domain evidence, not a second self-DNA root.",
        "flowguard": _flowguard_identity(),
        "readiness": bundle.readiness_ledger.to_dict(),
        "dna_qualification": qualification.to_dict(),
    }, bundle


def check(root: str | Path, *, compact: bool = False) -> tuple[dict[str, Any], int]:
    root_path = Path(root).resolve()
    payload, _bundle = _build(root_path)
    if compact:
        readiness = payload.get("readiness", {})
        payload = {
            "report_kind": payload.get("report_kind"),
            "software_id": payload.get("software_id"),
            "target_kind": payload.get("target_kind"),
            "status": payload.get("status"),
            "ok": payload.get("ok"),
            "root": payload.get("root"),
            "claim_boundary": payload.get("claim_boundary"),
            "flowguard": payload.get("flowguard"),
            "native_directory_only": payload.get("native_directory_only"),
            "gap": payload.get("gap"),
            "readiness": {
                key: readiness[key]
                for key in ("status", "deepest_proven_layer", "first_gap", "gap_count", "implementation_admitted", "rows")
                if key in readiness
            },
            "dna_qualification": payload.get("dna_qualification"),
        }
    return payload, 0 if payload.get("ok") else 1


def _reject_disk_export(root: str | Path, output: str | Path) -> tuple[dict[str, Any], int]:
    root_path = Path(root).resolve()
    output_path = Path(output).resolve()
    return _blocked(
        root_path,
        "native_directory_only",
        "PhysicsGuard software DNA is authoritative only in the repository-native FlowGuard directory; disk export and materialization are retired.",
    ) | {"rejected_output": str(output_path)}, 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="physicsguard self-dna")
    sub = parser.add_subparsers(dest="command", required=True)
    check_parser = sub.add_parser("check", help="audit the FlowGuard-owned repository self-DNA")
    check_parser.add_argument("--root", default=".")
    check_parser.add_argument("--compact", action="store_true")
    export_parser = sub.add_parser("export", help="retired: self-DNA is repository-native only")
    export_parser.add_argument("--root", default=".")
    export_parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload, code = check(args.root, compact=args.compact) if args.command == "check" else _reject_disk_export(args.root, args.output)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return code


__all__ = ["check", "main"]
