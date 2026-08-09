"""Resolve the one current SkillGuard consumer/install authority for PhysicsGuard.

This module owns no consumer-file, manifest, transaction, receipt, lock, or
rollback semantics.  It only freezes the exact PhysicsGuard maintenance-unit
membership and loads the public API from the explicitly selected installed
SkillGuard tree after validating that module identity.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib
from types import ModuleType
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlparse


PHYSICSGUARD_MAINTENANCE_UNIT_ID = "unit:physicsguard-family"
PHYSICSGUARD_SKILL_IDS = (
    "physicsguard-ai-debugging",
    "physicsguard-audit-closure",
    "physicsguard-candidate-model-blueprint",
    "physicsguard-model-dataset-validation",
    "physicsguard-model-library",
    "physicsguard-model-understanding-preflight",
    "physicsguard-project-adoption",
    "physicsguard-project-evidence-registry",
    "physicsguard-signal-mapping-review",
    "physicsguard-test-file-contract-review",
)
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
DEFAULT_SKILLGUARD_ROOT = DEFAULT_CODEX_HOME / "skills" / "skillguard"


class SkillGuardAuthorityUnavailable(RuntimeError):
    """The requested installed SkillGuard API is missing or has another owner."""


@dataclass(frozen=True)
class PackageTreeFingerprint:
    """A complete cache-independent byte inventory for one Python package tree."""

    root: Path
    sha256: str
    file_count: int
    files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PythonPackageAuthority:
    """One metadata/direct-url/package-tree authority for an import package."""

    distribution_name: str
    distribution_version: str
    package_name: str
    package_root: Path
    package_tree_sha256: str
    package_file_count: int
    direct_url_sha256: str | None
    project_file_sha256: str | None
    authority_sha256: str


@dataclass(frozen=True)
class SkillGuardConsumerApi:
    skillguard_root: Path
    scripts_root: Path
    consumer_module_path: Path
    consumer_module_sha256: str
    consumer_distribution_plan: Callable[..., dict[str, Any]]
    audit_consumer_distribution: Callable[..., dict[str, Any]]
    prepare_target_stage: Callable[..., dict[str, Any]] | None = None
    verify_target_stage: Callable[..., dict[str, Any]] | None = None
    activate_target_stage: Callable[..., dict[str, Any]] | None = None
    rollback_target_install: Callable[..., dict[str, Any]] | None = None
    target_installation_module_path: Path | None = None
    target_installation_module_sha256: str | None = None
    package_root: Path | None = None
    package_tree_sha256: str | None = None
    package_file_count: int | None = None
    distribution_package_root: Path | None = None
    distribution_package_tree_sha256: str | None = None
    distribution_version: str | None = None
    distribution_direct_url_sha256: str | None = None
    distribution_authority_sha256: str | None = None

    def authority_record(self) -> dict[str, Any]:
        return {
            "skillguard_root": str(self.skillguard_root),
            "scripts_root": str(self.scripts_root),
            "consumer_module_path": str(self.consumer_module_path),
            "consumer_module_sha256": self.consumer_module_sha256,
            "target_installation_module_path": (
                str(self.target_installation_module_path)
                if self.target_installation_module_path is not None
                else None
            ),
            "target_installation_module_sha256": self.target_installation_module_sha256,
            "package_root": str(self.package_root) if self.package_root is not None else None,
            "package_tree_sha256": self.package_tree_sha256,
            "package_file_count": self.package_file_count,
            "distribution_package_root": (
                str(self.distribution_package_root)
                if self.distribution_package_root is not None
                else None
            ),
            "distribution_package_tree_sha256": (
                self.distribution_package_tree_sha256
            ),
            "distribution_version": self.distribution_version,
            "distribution_direct_url_sha256": (
                self.distribution_direct_url_sha256
            ),
            "distribution_authority_sha256": self.distribution_authority_sha256,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical_json_sha256(value: object) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _canonical_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def path_is_link_or_reparse(path: Path) -> bool:
    """Return true for symlinks, junctions, or unreadable path entities."""

    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def fingerprint_python_package_tree(package_root: Path) -> PackageTreeFingerprint:
    """Fingerprint every non-cache file under one safe package root."""

    lexical_root = Path(package_root).expanduser().absolute()
    if path_is_link_or_reparse(lexical_root):
        raise SkillGuardAuthorityUnavailable(
            f"python_package_root_unsafe_link:{lexical_root}"
        )
    try:
        root = lexical_root.resolve(strict=True)
    except OSError as exc:
        raise SkillGuardAuthorityUnavailable(
            f"python_package_root_missing:{type(exc).__name__}:{lexical_root}"
        ) from exc
    if not root.is_dir():
        raise SkillGuardAuthorityUnavailable(
            f"python_package_root_not_directory:{root}"
        )
    if not (root / "__init__.py").is_file():
        raise SkillGuardAuthorityUnavailable(
            f"python_package_init_missing:{root / '__init__.py'}"
        )

    rows: list[tuple[str, str]] = []
    for current_text, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(current_text)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            if name == "__pycache__":
                continue
            candidate = current / name
            if path_is_link_or_reparse(candidate):
                raise SkillGuardAuthorityUnavailable(
                    f"python_package_tree_unsafe_directory:{candidate}"
                )
            kept_directories.append(name)
        directory_names[:] = kept_directories
        for name in sorted(file_names):
            candidate = current / name
            if candidate.suffix.lower() in {".pyc", ".pyo"}:
                continue
            if path_is_link_or_reparse(candidate):
                raise SkillGuardAuthorityUnavailable(
                    f"python_package_tree_unsafe_file:{candidate}"
                )
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise SkillGuardAuthorityUnavailable(
                    "python_package_tree_file_unreadable:"
                    f"{type(exc).__name__}:{candidate}"
                ) from exc
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise SkillGuardAuthorityUnavailable(
                    f"python_package_tree_file_outside_root:{resolved}"
                )
            rows.append((resolved.relative_to(root).as_posix(), _sha256(resolved)))
    if not rows:
        raise SkillGuardAuthorityUnavailable(f"python_package_tree_empty:{root}")
    frozen_rows = tuple(sorted(rows))
    return PackageTreeFingerprint(
        root=root,
        sha256=_canonical_json_sha256(frozen_rows),
        file_count=len(frozen_rows),
        files=frozen_rows,
    )


def _path_from_file_url(url: str, *, distribution_name: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "file" or parsed.netloc not in {"", "localhost"}:
        raise SkillGuardAuthorityUnavailable(
            f"distribution_direct_url_not_local_file:{distribution_name}"
        )
    raw_path = unquote(parsed.path)
    if os.name == "nt" and re.match(r"^/[A-Za-z]:", raw_path):
        raw_path = raw_path[1:]
    lexical = Path(raw_path).expanduser().absolute()
    if path_is_link_or_reparse(lexical):
        raise SkillGuardAuthorityUnavailable(
            f"distribution_source_root_unsafe:{distribution_name}:{lexical}"
        )
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise SkillGuardAuthorityUnavailable(
            "distribution_source_root_missing:"
            f"{distribution_name}:{type(exc).__name__}:{lexical}"
        ) from exc
    if not resolved.is_dir():
        raise SkillGuardAuthorityUnavailable(
            f"distribution_source_root_not_directory:{distribution_name}:{resolved}"
        )
    return resolved


def _editable_distribution_package_root(
    source_root: Path,
    *,
    distribution_name: str,
    distribution_version: str,
    package_name: str,
) -> tuple[Path, str]:
    pyproject_path = source_root / "pyproject.toml"
    if path_is_link_or_reparse(pyproject_path) or not pyproject_path.is_file():
        raise SkillGuardAuthorityUnavailable(
            f"distribution_pyproject_missing:{distribution_name}:{pyproject_path}"
        )
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SkillGuardAuthorityUnavailable(
            "distribution_pyproject_unreadable:"
            f"{distribution_name}:{type(exc).__name__}:{pyproject_path}"
        ) from exc
    project = pyproject.get("project")
    if not isinstance(project, Mapping):
        raise SkillGuardAuthorityUnavailable(
            f"distribution_pyproject_project_missing:{distribution_name}"
        )
    project_name = str(project.get("name", ""))
    project_version = str(project.get("version", ""))
    if _canonical_distribution_name(project_name) != _canonical_distribution_name(
        distribution_name
    ):
        raise SkillGuardAuthorityUnavailable(
            "distribution_pyproject_name_mismatch:"
            f"expected={distribution_name}:observed={project_name}"
        )
    if project_version != distribution_version:
        raise SkillGuardAuthorityUnavailable(
            "distribution_pyproject_version_mismatch:"
            f"metadata={distribution_version}:project={project_version}"
        )

    tool = pyproject.get("tool")
    setuptools = tool.get("setuptools") if isinstance(tool, Mapping) else None
    package_dirs = (
        setuptools.get("package-dir") if isinstance(setuptools, Mapping) else None
    )
    relative_base = Path(".")
    explicit_package_path: Path | None = None
    if isinstance(package_dirs, Mapping):
        if package_name in package_dirs:
            explicit_package_path = Path(str(package_dirs[package_name]))
        elif "" in package_dirs:
            relative_base = Path(str(package_dirs[""]))
    for candidate in (relative_base, explicit_package_path):
        if candidate is None:
            continue
        if candidate.is_absolute() or ".." in candidate.parts:
            raise SkillGuardAuthorityUnavailable(
                f"distribution_package_dir_unsafe:{distribution_name}:{candidate}"
            )
    package_root = (
        source_root / explicit_package_path
        if explicit_package_path is not None
        else source_root / relative_base / package_name
    )
    return package_root, _sha256(pyproject_path)


def resolve_python_package_authority(
    distribution_name: str,
    package_name: str,
) -> PythonPackageAuthority:
    """Resolve one distribution and the exact package tree it owns."""

    try:
        distribution = importlib.metadata.distribution(distribution_name)
    except (importlib.metadata.PackageNotFoundError, OSError) as exc:
        raise SkillGuardAuthorityUnavailable(
            f"distribution_metadata_unavailable:{distribution_name}:{type(exc).__name__}"
        ) from exc
    metadata_name = str(distribution.metadata.get("Name") or "")
    if _canonical_distribution_name(metadata_name) != _canonical_distribution_name(
        distribution_name
    ):
        raise SkillGuardAuthorityUnavailable(
            "distribution_metadata_name_mismatch:"
            f"expected={distribution_name}:observed={metadata_name}"
        )
    distribution_version = str(distribution.version)
    if not distribution_version:
        raise SkillGuardAuthorityUnavailable(
            f"distribution_metadata_version_missing:{distribution_name}"
        )

    direct_url_text = distribution.read_text("direct_url.json")
    direct_url_sha256: str | None = None
    project_file_sha256: str | None = None
    if direct_url_text:
        try:
            direct_url = json.loads(direct_url_text)
        except json.JSONDecodeError as exc:
            raise SkillGuardAuthorityUnavailable(
                f"distribution_direct_url_invalid:{distribution_name}"
            ) from exc
        if not isinstance(direct_url, Mapping):
            raise SkillGuardAuthorityUnavailable(
                f"distribution_direct_url_not_object:{distribution_name}"
            )
        directory_info = direct_url.get("dir_info")
        if not isinstance(directory_info, Mapping) or directory_info.get(
            "editable"
        ) is not True:
            raise SkillGuardAuthorityUnavailable(
                f"distribution_direct_url_not_editable:{distribution_name}"
            )
        source_root = _path_from_file_url(
            str(direct_url.get("url", "")), distribution_name=distribution_name
        )
        package_root, project_file_sha256 = _editable_distribution_package_root(
            source_root,
            distribution_name=distribution_name,
            distribution_version=distribution_version,
            package_name=package_name,
        )
        direct_url_sha256 = _canonical_json_sha256(direct_url)
    else:
        files = tuple(distribution.files or ())
        owned_prefix = package_name.replace(".", "/") + "/"
        if not any(str(path).replace("\\", "/").startswith(owned_prefix) for path in files):
            raise SkillGuardAuthorityUnavailable(
                f"distribution_package_inventory_missing:{distribution_name}:{package_name}"
            )
        package_root = Path(distribution.locate_file(package_name))

    tree = fingerprint_python_package_tree(package_root)
    authority_sha256 = _canonical_json_sha256(
        {
            "distribution_name": _canonical_distribution_name(metadata_name),
            "distribution_version": distribution_version,
            "package_name": package_name,
            "package_tree_sha256": tree.sha256,
            "package_file_count": tree.file_count,
            "direct_url_sha256": direct_url_sha256,
            "project_file_sha256": project_file_sha256,
        }
    )
    return PythonPackageAuthority(
        distribution_name=metadata_name,
        distribution_version=distribution_version,
        package_name=package_name,
        package_root=tree.root,
        package_tree_sha256=tree.sha256,
        package_file_count=tree.file_count,
        direct_url_sha256=direct_url_sha256,
        project_file_sha256=project_file_sha256,
        authority_sha256=authority_sha256,
    )


def verify_loaded_package_modules(package_name: str, package_root: Path) -> None:
    """Require every already-loaded module in a package to have one root owner."""

    root = Path(package_root).resolve(strict=True)
    module_names = sorted(
        name
        for name in sys.modules
        if name == package_name or name.startswith(package_name + ".")
    )
    if package_name not in module_names:
        raise SkillGuardAuthorityUnavailable(
            f"package_root_module_not_loaded:{package_name}"
        )
    for module_name in module_names:
        module = sys.modules[module_name]
        module_file = getattr(module, "__file__", None)
        if not module_file:
            raise SkillGuardAuthorityUnavailable(
                f"package_loaded_module_path_missing:{module_name}"
            )
        try:
            observed = Path(module_file).resolve(strict=True)
        except OSError as exc:
            raise SkillGuardAuthorityUnavailable(
                "package_loaded_module_path_unreadable:"
                f"{module_name}:{type(exc).__name__}"
            ) from exc
        if not observed.is_relative_to(root):
            raise SkillGuardAuthorityUnavailable(
                "package_loaded_module_owner_mismatch:"
                f"{module_name}:expected_root={root}:observed={observed}"
            )
        if module_name == package_name and observed != root / "__init__.py":
            raise SkillGuardAuthorityUnavailable(
                "package_root_module_owner_mismatch:"
                f"{module_name}:expected={root / '__init__.py'}:observed={observed}"
            )
        module_spec = getattr(module, "__spec__", None)
        search_locations = getattr(module_spec, "submodule_search_locations", None)
        if search_locations is not None:
            for location in search_locations:
                try:
                    observed_location = Path(location).resolve(strict=True)
                except OSError as exc:
                    raise SkillGuardAuthorityUnavailable(
                        "package_loaded_search_path_unreadable:"
                        f"{module_name}:{type(exc).__name__}"
                    ) from exc
                if not observed_location.is_relative_to(root):
                    raise SkillGuardAuthorityUnavailable(
                        "package_loaded_search_path_owner_mismatch:"
                        f"{module_name}:expected_root={root}:observed={observed_location}"
                    )


def _require_owned_path(path: Path, owner_root: Path, *, kind: str) -> Path:
    lexical = path.absolute()
    if path_is_link_or_reparse(lexical):
        raise SkillGuardAuthorityUnavailable(f"{kind}_unsafe_link:{lexical}")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise SkillGuardAuthorityUnavailable(
            f"{kind}_missing:{type(exc).__name__}:{lexical}"
        ) from exc
    if not resolved.is_relative_to(owner_root):
        raise SkillGuardAuthorityUnavailable(f"{kind}_outside_owner:{resolved}")
    return resolved


def _load_exact_module(
    module_name: str,
    expected_path: Path,
    scripts_root: Path,
) -> ModuleType:
    loaded = sys.modules.get(module_name)
    inserted = False
    if loaded is None:
        scripts_text = str(scripts_root)
        if scripts_text not in sys.path:
            sys.path.insert(0, scripts_text)
            inserted = True
        try:
            loaded = importlib.import_module(module_name)
        except (ImportError, OSError) as exc:
            raise SkillGuardAuthorityUnavailable(
                f"skillguard_api_import_failed:{module_name}:{type(exc).__name__}:{exc}"
            ) from exc
        finally:
            if inserted:
                sys.path.remove(scripts_text)
    module_file = getattr(loaded, "__file__", None)
    if not module_file:
        raise SkillGuardAuthorityUnavailable(
            f"skillguard_api_module_path_missing:{module_name}"
        )
    try:
        observed = Path(module_file).resolve(strict=True)
    except OSError as exc:
        raise SkillGuardAuthorityUnavailable(
            f"skillguard_api_module_path_unreadable:{module_name}:{type(exc).__name__}"
        ) from exc
    if observed != expected_path:
        raise SkillGuardAuthorityUnavailable(
            "skillguard_api_module_owner_mismatch:"
            f"{module_name}:expected={expected_path}:observed={observed}"
        )
    return loaded


def _require_callable(module: ModuleType, name: str) -> Callable[..., dict[str, Any]]:
    value = getattr(module, name, None)
    if not callable(value):
        raise SkillGuardAuthorityUnavailable(
            f"skillguard_api_callable_missing:{module.__name__}.{name}"
        )
    return value


def load_skillguard_consumer_api(
    skillguard_root: Path = DEFAULT_SKILLGUARD_ROOT,
    *,
    require_installation: bool = False,
) -> SkillGuardConsumerApi:
    """Load one byte-bound installed/distribution API and reject other owners."""

    try:
        lexical_root = Path(skillguard_root).expanduser().absolute()
        if path_is_link_or_reparse(lexical_root):
            raise SkillGuardAuthorityUnavailable(
                f"skillguard_root_unsafe:{lexical_root}"
            )
        root = lexical_root.resolve(strict=True)
    except OSError as exc:
        raise SkillGuardAuthorityUnavailable(
            f"skillguard_root_missing:{type(exc).__name__}:{skillguard_root}"
        ) from exc
    if not root.is_dir():
        raise SkillGuardAuthorityUnavailable(f"skillguard_root_unsafe:{root}")
    scripts = _require_owned_path(root / "scripts", root, kind="skillguard_scripts_root")
    if not scripts.is_dir():
        raise SkillGuardAuthorityUnavailable(f"skillguard_scripts_root_not_directory:{scripts}")
    package = _require_owned_path(
        scripts / "skillguard_v2", scripts, kind="skillguard_api_package"
    )
    if not package.is_dir():
        raise SkillGuardAuthorityUnavailable(f"skillguard_api_package_not_directory:{package}")
    selected_tree_before = fingerprint_python_package_tree(package)
    distribution_authority = resolve_python_package_authority(
        "skillguard", "skillguard_v2"
    )
    distribution_tree_before = fingerprint_python_package_tree(
        distribution_authority.package_root
    )
    if (
        distribution_tree_before.sha256
        != distribution_authority.package_tree_sha256
        or distribution_tree_before.file_count
        != distribution_authority.package_file_count
    ):
        raise SkillGuardAuthorityUnavailable(
            "skillguard_distribution_tree_changed_during_metadata_resolution:"
            f"metadata={distribution_authority.package_tree_sha256}:"
            f"observed={distribution_tree_before.sha256}"
        )
    if selected_tree_before.files != distribution_tree_before.files:
        raise SkillGuardAuthorityUnavailable(
            "skillguard_installed_distribution_tree_mismatch:"
            f"installed={selected_tree_before.sha256}:"
            f"distribution={distribution_tree_before.sha256}"
        )
    package_init_path = _require_owned_path(
        package / "__init__.py", scripts, kind="skillguard_api_package_init"
    )
    if not package_init_path.is_file():
        raise SkillGuardAuthorityUnavailable(
            f"skillguard_api_package_init_not_file:{package_init_path}"
        )
    _load_exact_module("skillguard_v2", package_init_path, scripts)
    consumer_path = _require_owned_path(
        package / "consumer_distribution.py",
        scripts,
        kind="skillguard_consumer_api",
    )
    if not consumer_path.is_file():
        raise SkillGuardAuthorityUnavailable(
            f"skillguard_consumer_api_not_file:{consumer_path}"
        )
    consumer = _load_exact_module(
        "skillguard_v2.consumer_distribution", consumer_path, scripts
    )

    installation = None
    installation_path = None
    if require_installation:
        installation_path = _require_owned_path(
            package / "target_installation.py",
            scripts,
            kind="skillguard_target_installation_api",
        )
        if not installation_path.is_file():
            raise SkillGuardAuthorityUnavailable(
                f"skillguard_target_installation_api_not_file:{installation_path}"
            )
        installation = _load_exact_module(
            "skillguard_v2.target_installation", installation_path, scripts
        )

    verify_loaded_package_modules("skillguard_v2", package)
    selected_tree_after = fingerprint_python_package_tree(package)
    distribution_tree_after = fingerprint_python_package_tree(
        distribution_authority.package_root
    )
    if selected_tree_before.files != selected_tree_after.files:
        raise SkillGuardAuthorityUnavailable(
            "skillguard_installed_tree_changed_during_authority_freeze:"
            f"before={selected_tree_before.sha256}:after={selected_tree_after.sha256}"
        )
    if distribution_tree_before.files != distribution_tree_after.files:
        raise SkillGuardAuthorityUnavailable(
            "skillguard_distribution_tree_changed_during_authority_freeze:"
            f"before={distribution_tree_before.sha256}:"
            f"after={distribution_tree_after.sha256}"
        )
    if selected_tree_after.files != distribution_tree_after.files:
        raise SkillGuardAuthorityUnavailable(
            "skillguard_installed_distribution_tree_mismatch_after_import:"
            f"installed={selected_tree_after.sha256}:"
            f"distribution={distribution_tree_after.sha256}"
        )

    return SkillGuardConsumerApi(
        skillguard_root=root,
        scripts_root=scripts,
        consumer_module_path=consumer_path,
        consumer_module_sha256=_sha256(consumer_path),
        consumer_distribution_plan=_require_callable(
            consumer, "consumer_distribution_plan"
        ),
        audit_consumer_distribution=_require_callable(
            consumer, "audit_consumer_distribution"
        ),
        prepare_target_stage=(
            _require_callable(installation, "prepare_target_stage")
            if installation is not None
            else None
        ),
        verify_target_stage=(
            _require_callable(installation, "verify_target_stage")
            if installation is not None
            else None
        ),
        activate_target_stage=(
            _require_callable(installation, "activate_target_stage")
            if installation is not None
            else None
        ),
        rollback_target_install=(
            _require_callable(installation, "rollback_target_install")
            if installation is not None
            else None
        ),
        target_installation_module_path=installation_path,
        target_installation_module_sha256=(
            _sha256(installation_path) if installation_path is not None else None
        ),
        package_root=selected_tree_after.root,
        package_tree_sha256=selected_tree_after.sha256,
        package_file_count=selected_tree_after.file_count,
        distribution_package_root=distribution_tree_after.root,
        distribution_package_tree_sha256=distribution_tree_after.sha256,
        distribution_version=distribution_authority.distribution_version,
        distribution_direct_url_sha256=distribution_authority.direct_url_sha256,
        distribution_authority_sha256=distribution_authority.authority_sha256,
    )


def physicsguard_member_roots(repository_root: Path) -> tuple[tuple[str, Path], ...]:
    """Return the exact ten source roots or block on inventory drift."""

    repository = Path(repository_root).resolve(strict=True)
    lexical_skill_root = repository / "skill"
    if path_is_link_or_reparse(lexical_skill_root):
        raise ValueError(f"physicsguard_skill_root_unsafe:{lexical_skill_root}")
    skill_root = lexical_skill_root.resolve(strict=True)
    actual = {
        path.name
        for path in skill_root.iterdir()
        if path.is_dir() and not path.is_symlink()
    }
    expected = set(PHYSICSGUARD_SKILL_IDS)
    if actual != expected:
        raise ValueError(
            "physicsguard_skill_inventory_mismatch:"
            f"missing={sorted(expected - actual)}:unexpected={sorted(actual - expected)}"
        )
    rows: list[tuple[str, Path]] = []
    for skill_id in PHYSICSGUARD_SKILL_IDS:
        lexical_member = skill_root / skill_id
        if path_is_link_or_reparse(lexical_member):
            raise ValueError(
                f"physicsguard_skill_root_unsafe:{skill_id}:{lexical_member}"
            )
        member = lexical_member.resolve(strict=True)
        if not member.is_relative_to(repository):
            raise ValueError(f"physicsguard_skill_root_unsafe:{skill_id}:{member}")
        rows.append((skill_id, member))
    return tuple(rows)


def load_member_contract(member_root: Path, skill_id: str) -> dict[str, Any]:
    """Load the exact compiled author contract needed by SkillGuard's planner."""

    member = Path(member_root).resolve(strict=True)
    control_lexical = member / ".skillguard"
    if path_is_link_or_reparse(control_lexical) or not control_lexical.is_dir():
        raise ValueError(f"member_author_control_root_unsafe:{skill_id}")
    control = control_lexical.resolve(strict=True)
    if not control.is_relative_to(member):
        raise ValueError(f"member_author_control_root_outside_member:{skill_id}")
    path_lexical = control / "compiled-contract.json"
    if path_is_link_or_reparse(path_lexical) or not path_lexical.is_file():
        raise ValueError(f"member_compiled_contract_missing:{skill_id}")
    path = path_lexical.resolve(strict=True)
    if not path.is_relative_to(control):
        raise ValueError(f"member_compiled_contract_outside_control:{skill_id}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"member_compiled_contract_unreadable:{skill_id}:{type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError(f"member_compiled_contract_not_object:{skill_id}")
    if value.get("skill_id") != skill_id:
        raise ValueError(f"member_compiled_contract_skill_mismatch:{skill_id}")
    if value.get("maintenance_unit_id") != PHYSICSGUARD_MAINTENANCE_UNIT_ID:
        raise ValueError(f"member_compiled_contract_unit_mismatch:{skill_id}")
    member_ids = value.get("member_skill_ids")
    if sorted(map(str, member_ids or [])) != sorted(PHYSICSGUARD_SKILL_IDS):
        raise ValueError(f"member_compiled_contract_inventory_mismatch:{skill_id}")
    projection = value.get("consumer_projection")
    if not isinstance(projection, Mapping):
        raise ValueError(f"member_consumer_projection_missing:{skill_id}")
    if (
        projection.get("projection_id") != "projection:consumer-distribution"
        or projection.get("release_manifest_path") != "consumer-release.json"
    ):
        raise ValueError(f"member_consumer_projection_identity_wrong:{skill_id}")
    return value


__all__ = [
    "DEFAULT_CODEX_HOME",
    "DEFAULT_SKILLGUARD_ROOT",
    "PHYSICSGUARD_MAINTENANCE_UNIT_ID",
    "PHYSICSGUARD_SKILL_IDS",
    "PackageTreeFingerprint",
    "PythonPackageAuthority",
    "SkillGuardAuthorityUnavailable",
    "SkillGuardConsumerApi",
    "fingerprint_python_package_tree",
    "load_member_contract",
    "load_skillguard_consumer_api",
    "path_is_link_or_reparse",
    "physicsguard_member_roots",
    "resolve_python_package_authority",
    "verify_loaded_package_modules",
]
