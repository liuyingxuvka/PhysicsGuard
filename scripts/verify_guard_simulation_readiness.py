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

sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from check_installed_physicsguard_skills import check_installed_skills  # noqa: E402
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
        metadata_version = importlib.metadata.version("physicsguard")
        ok = metadata_version == module_version == expected_version and module_path.is_relative_to(repository_root.resolve() / "src" / "physicsguard")
        return {"check": "canonical_package_identity", "ok": ok, "expected_version": expected_version, "metadata_version": metadata_version, "module_version": module_version, "module_path": str(module_path)}
    except (ImportError, OSError, ValueError, KeyError, AttributeError) as exc:
        return {"check": "canonical_package_identity", "ok": False, "expected_version": expected_version, "findings": [f"{type(exc).__name__}:{exc}"]}


def build_report(repository_root: Path = ROOT, installed_root: Path = HOME_SKILLS) -> dict[str, Any]:
    package = _check_package_identity(repository_root)
    installation = check_installed_skills(installed_root, repository_root=repository_root)
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
