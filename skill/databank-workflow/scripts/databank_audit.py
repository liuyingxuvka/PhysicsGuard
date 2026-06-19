from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_closure_check import check_closure
from databank_common import as_list, closure_result, dump_json, load_struct, write_json
from databank_contract_check import check_contracts
from databank_freshness_check import check_freshness
from databank_nav_render import render_nav
from databank_query import query_catalog
from databank_root_check import check_root


def _glob_structs(root: Path, relative: str) -> list[Path]:
    directory = root / relative
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml"}
    )


def _status_rank(status: str) -> int:
    return {"pass": 0, "partial": 1, "downgraded": 2, "blocked": 3}.get(status, 3)


def _aggregate_status(results: list[dict[str, Any]]) -> str:
    if not results:
        return "blocked"
    worst = max(results, key=lambda item: _status_rank(str(item.get("status"))))
    return str(worst.get("status"))


def _section(name: str, path: str | Path | None, result: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "path": str(path) if path else "", "status": result.get("status"), "result": result}


def audit_database(
    database_root: str | Path,
    *,
    contracts: list[str | Path] | None = None,
    freshness: list[str | Path] | None = None,
    providers: list[str | Path] | None = None,
    catalog: str | Path | None = None,
    nav: str | Path | None = None,
    queries: list[str] | None = None,
) -> dict[str, Any]:
    root = Path(database_root).resolve()
    sections: list[dict[str, Any]] = []

    root_result = check_root(root)
    sections.append(_section("root", root, root_result))

    contract_paths = [Path(path) for path in (contracts or [])] or _glob_structs(root, "contracts")
    for path in contract_paths:
        sections.append(_section("contracts", path, check_contracts(path, check_paths=True, base_path=root)))

    freshness_paths = [Path(path) for path in (freshness or [])]
    default_freshness = root / "freshness.json"
    if not freshness_paths and default_freshness.exists():
        freshness_paths = [default_freshness]
    for path in freshness_paths:
        sections.append(_section("freshness", path, check_freshness(path)))

    provider_paths = [Path(path) for path in (providers or [])] or _glob_structs(root, "provider_results")
    catalog_path = Path(catalog) if catalog else root / "database_catalog.json"
    if provider_paths:
        sections.append(_section("closure", catalog_path, check_closure(provider_paths, catalog_path if catalog_path.exists() else None)))
    else:
        sections.append(
            _section(
                "closure",
                catalog_path,
                closure_result(
                    "blocked",
                    missing_inputs=[{"id": "provider_results", "path": str(root / "provider_results"), "reason": "no_provider_results"}],
                    unsafe_claim_boundary="Cannot make broad DataBank claims without provider closure results.",
                    next_actions=["Add provider closure envelopes or run databank_provider_adapter.py."],
                ),
            )
        )

    nav_path = Path(nav) if nav else root / "navigation" / "nav_manifest.json"
    if nav_path.exists():
        sections.append(_section("navigation", nav_path, render_nav(nav_path)))

    query_specs = queries or []
    if catalog_path.exists():
        for spec in query_specs:
            if "=" not in spec:
                sections.append(
                    _section(
                        "query",
                        catalog_path,
                        closure_result(
                            "blocked",
                            missing_inputs=[{"id": "query", "value": spec, "reason": "expected_FIELD=VALUE"}],
                            unsafe_claim_boundary="Malformed query was not executed.",
                        ),
                    )
                )
                continue
            field, value = spec.split("=", 1)
            sections.append(_section("query", catalog_path, query_catalog(catalog_path, field, value)))

    status = _aggregate_status([section["result"] for section in sections])
    missing_inputs: list[Any] = []
    stale_evidence: list[Any] = []
    skipped_checks: list[Any] = []
    evidence: list[Any] = []
    next_actions: list[Any] = []
    for section in sections:
        result = section["result"]
        evidence.append({"id": section["name"], "path": section["path"], "status": result.get("status")})
        missing_inputs.extend(as_list(result.get("missing_inputs")))
        stale_evidence.extend(as_list(result.get("stale_evidence")))
        skipped_checks.extend(as_list(result.get("skipped_checks")))
        next_actions.extend(as_list(result.get("next_actions")))

    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=missing_inputs,
        stale_evidence=stale_evidence,
        skipped_checks=skipped_checks,
        safe_claim="DataBank audit passed for the checked root." if status == "pass" else "",
        unsafe_claim_boundary="" if status == "pass" else "Do not claim this DataBank root is validated, reusable, or complete.",
        next_actions=next_actions,
        extra={"database_root": str(root), "sections": sections},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a one-command DataBank audit over an explicit database root.")
    parser.add_argument("database_root", help="Explicit DataBank root")
    parser.add_argument("--contracts", action="append", help="Contract file; defaults to contracts/*.json/yaml")
    parser.add_argument("--freshness", action="append", help="Freshness manifest")
    parser.add_argument("--provider", action="append", help="Provider closure file; defaults to provider_results/*.json/yaml")
    parser.add_argument("--catalog", help="Catalog file; defaults to database_catalog.json")
    parser.add_argument("--nav", help="Navigation manifest; defaults to navigation/nav_manifest.json")
    parser.add_argument("--query", action="append", help="Query smoke spec FIELD=VALUE")
    parser.add_argument("--output", help="Optional audit JSON output path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = audit_database(
        args.database_root,
        contracts=args.contracts,
        freshness=args.freshness,
        providers=args.provider,
        catalog=args.catalog,
        nav=args.nav,
        queries=args.query,
    )
    if args.output:
        dump_json(result, args.output)
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
