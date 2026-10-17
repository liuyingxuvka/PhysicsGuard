"""Read the current FlowGuard map without executing models or claiming test success.

The physical-object blueprint is a separate domain route.  This command reads
repository code/model/test bindings; affected execution belongs to FlowGuard's
existing impact and model/test commands, without a stored PASS certificate.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
from typing import Any

REPORT_KIND = "physicsguard.flowguard_software_self_dna_report.v1"


def _native_directory_only(root: Path) -> dict[str, Any]:
    return {"kind": "native_directory_only", "status": "enforced", "canonical_root": str(root),
            "canonical_authority": "repository_flowguard_map", "disk_export": "prohibited",
            "bundle_materialization": "prohibited", "alternate_head": "prohibited", "cache_authority": "prohibited"}


def _flowguard_identity() -> dict[str, str]:
    try:
        version = importlib.metadata.version("flowguard")
    except importlib.metadata.PackageNotFoundError:
        version = "unavailable"
    try:
        import flowguard
        from flowguard.map.common import SCHEMA
        return {"package": "flowguard", "version": version, "schema_version": SCHEMA,
                "module": str(Path(flowguard.__file__).resolve())}
    except ImportError as exc:
        return {"package": "flowguard", "version": version, "import_error": str(exc)}


def _base(root: Path) -> dict[str, Any]:
    return {"report_kind": REPORT_KIND, "software_id": "physicsguard", "target_kind": "software",
            "root": str(root), "native_directory_only": _native_directory_only(root),
            "flowguard": _flowguard_identity(),
            "claim_boundary": "Current repository map and code/model/test bindings only. Models and tests are not run by this command; content hashes are current observations, not past execution or freshness certificates. Physical-object blueprints remain separate.",
            "model_execution": "not_run", "test_execution": "not_run"}


def _blocked(root: Path, code: str, message: str) -> dict[str, Any]:
    return {**_base(root), "status": "blocked", "ok": False,
            "gap": {"code": code, "message": message},
            "readiness": {"status": "blocked", "first_gap": code, "gap_count": 1}}


def _build(root: Path) -> dict[str, Any]:
    try:
        from flowguard.map.check import run_check
        from flowguard.map.common import matches_any
        from flowguard.map.inventory import build_inventory
        from flowguard.map.mapfile import (MapError, component_files, component_graph,
                                           fingerprint, ignore_patterns, load_map, model_registry)
    except ImportError as exc:
        return _blocked(root, "flowguard_toolchain_unavailable", str(exc))
    try:
        data = load_map(root)
        inv = build_inventory(root, ignore_patterns(data))
        findings = run_check(root, data, inv, strict=True)
        registry = model_registry(root, data)
        graph = component_graph(data, inv)
        rows = []
        for component in data["components"]:
            cid = component["id"]
            code = component_files(component, inv)
            tests = sorted(p for p in inv.tests if matches_any(p, component.get("tests", [])))
            models = sorted(component.get("models", []))
            model_sources = set(models)
            for model in models:
                path = Path(model)
                if path.name == "run_checks.py" and path.parts[:3] == (".flowguard", "verification", "owners"):
                    model_sources.update(p.relative_to(root).as_posix()
                                         for p in (root / ".flowguard/models/owners" / path.parent.name).glob("*.py"))
            model_sources = sorted(model_sources)
            rows.append({"id": cid, "summary": component["summary"], "responsibilities": component["responsibilities"],
                         "code": code, "code_fingerprint": fingerprint(root, code),
                         "confirmed_fingerprint": component.get("fingerprint", ""),
                         "tests": tests, "test_fingerprint": fingerprint(root, tests), "test_execution": "not_run",
                         "models": models, "model_sources": model_sources, "model_fingerprint": fingerprint(root, model_sources), "model_execution": "not_run",
                         "depends_on": sorted(graph[cid]),
                         "reverse_dependents": sorted(other for other, deps in graph.items() if cid in deps)})
        errors = [f for f in findings if f.level == "error"]
        first = errors[0].code if errors else ""
        result = {**_base(root), "status": "current" if not errors else "blocked", "ok": not errors,
                  "map": {"path": ".flowguard/map.json", "schema": data["schema"],
                          "fingerprint": fingerprint(root, [".flowguard/map.json"])},
                  "readiness": {"status": "current" if not errors else "blocked", "first_gap": first, "gap_count": len(errors)},
                  "components": rows,
                  "registered_models": [{"id": m.id, "path": m.path, "kind": m.kind, "execution": "not_run"} for m in registry.entries],
                  "findings": [{"level": f.level, "code": f.code, "component": f.component, "message": f.message} for f in findings]}
        if errors:
            result["gap"] = {"code": first, "message": errors[0].message}
        return result
    except (MapError, OSError, ValueError, KeyError) as exc:
        return _blocked(root, "flowguard_map_invalid", str(exc))


def check(root: str | Path, *, compact: bool = False) -> tuple[dict[str, Any], int]:
    payload = _build(Path(root).resolve())
    if compact:
        payload = {k: v for k, v in payload.items() if k not in {"components", "findings"}}
    return payload, 0 if payload.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="physicsguard self-dna")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("check", help="read current FlowGuard repository bindings; models/tests remain not_run")
    command.add_argument("--root", default=".")
    command.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    payload, code = check(args.root, compact=args.compact)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return code


__all__ = ["check", "main"]
