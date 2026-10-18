"""Check the PhysicsGuard package version/source and installed consumer file parity."""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
import tomllib
from typing import Any
from urllib.parse import unquote, urlparse

sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from check_installed_physicsguard_skills import blocked_installed_skill_audit, check_installed_skills  # noqa: E402
from install_physicsguard_skills import DEFAULT_CODEX_HOME, ROOT  # noqa: E402

HOME_SKILLS = DEFAULT_CODEX_HOME / "skills"


def _check_package_identity(repository_root: Path = ROOT) -> dict[str, Any]:
    expected_version = ""
    try:
        project = tomllib.loads((repository_root / "pyproject.toml").read_text(encoding="utf-8"))
        expected_version = str(project["project"]["version"])
        module = importlib.import_module("physicsguard")
        module_path = Path(module.__file__).resolve()
        module_version = str(module.__version__)
        distribution = importlib.metadata.distribution("physicsguard")
        metadata_version = distribution.version
        origins = {Path(distribution.locate_file(file)).resolve()
                   for file in distribution.files or ()
                   if str(file).replace("\\", "/").endswith("physicsguard/__init__.py")}
        direct_url = distribution.read_text("direct_url.json")
        if direct_url:
            editable = json.loads(direct_url)
            location = urlparse(str(editable.get("url", "")))
            if editable.get("dir_info", {}).get("editable") is True and location.scheme == "file" and not location.netloc:
                source_root = Path(unquote(location.path))
                origins.update((source_root / candidate).resolve()
                               for candidate in ("src/physicsguard/__init__.py", "physicsguard/__init__.py"))
        spec_origin = getattr(getattr(module, "__spec__", None), "origin", None)
        origin_matches = bool(spec_origin) and Path(spec_origin).resolve() == module_path and module_path in origins
        ok = metadata_version == module_version == expected_version and origin_matches
        return {"check": "canonical_package_identity", "ok": ok, "expected_version": expected_version, "metadata_version": metadata_version, "module_version": module_version, "module_path": str(module_path), "distribution_module_origins": sorted(str(path) for path in origins), "origin_matches_distribution": origin_matches}
    # Import executes external package code; ordinary failures must remain machine-readable.
    except Exception as exc:
        return {"check": "canonical_package_identity", "ok": False, "expected_version": expected_version, "findings": [f"{type(exc).__name__}:{exc}"]}


def build_report(repository_root: Path = ROOT, installed_root: Path = HOME_SKILLS) -> dict[str, Any]:
    """Return blocked JSON-compatible data on ordinary package or native audit failures."""
    package = _check_package_identity(repository_root)
    try:
        installation = check_installed_skills(installed_root, repository_root=repository_root)
    except Exception as exc:
        installation = blocked_installed_skill_audit(
            installed_root=installed_root, repository_root=repository_root,
            finding_type="installed_skill_audit_exception", detail=f"{type(exc).__name__}:{exc}",
        )
    ok = package["ok"] and installation["ok"]
    return {"artifact_kind": "physicsguard_runtime_readiness", "ok": ok, "status": "pass" if ok else "blocked", "package": package, "consumer_installation_audit": installation, "claim_boundary": "Checks package identity and consumer file parity only; executes no domain check or installation."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--installed-root", type=Path, default=HOME_SKILLS)
    args = parser.parse_args(argv)
    result = build_report(args.repository_root, args.installed_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
