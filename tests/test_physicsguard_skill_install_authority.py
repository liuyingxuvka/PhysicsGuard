from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace

import pytest

from scripts import physicsguard_skill_install_authority as install_authority
from scripts import upgrade_purpose_contracts as generator


ROOT = Path(__file__).resolve().parents[1]
SUITE_CHECKER_PATH = ROOT / ".flowguard" / "check_physicsguard_skill_suite_mesh.py"


def _load_suite_checker():
    spec = importlib.util.spec_from_file_location(
        "physicsguard_skill_suite_checker_for_authority_test",
        SUITE_CHECKER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generator_help_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    touched: list[str] = []
    monkeypatch.setattr(
        generator,
        "current_toolchain_identity",
        lambda **kwargs: touched.append("identity"),
    )
    monkeypatch.setattr(
        generator,
        "_run_generation_transaction",
        lambda *args, **kwargs: touched.append("generation"),
    )

    with pytest.raises(SystemExit) as exc_info:
        generator.main(argv=["--help"])

    assert exc_info.value.code == 0
    assert touched == []
    help_text = capsys.readouterr().out
    assert "authority-frozen" in help_text
    assert "staging transaction" in help_text


def _write_flowguard_project(path: Path, version: str, schema: str = "1.0") -> None:
    path.write_text(
        "[flowguard]\n"
        f'adopted_package_version = "{version}"\n'
        f'schema_version = "{schema}"\n',
        encoding="utf-8",
    )


def _write_physicsguard_versions(
    root: Path,
    *,
    pyproject_version: str = "3.2.1",
    version_file_version: str | None = None,
    source_version: str | None = None,
) -> None:
    (root / "src" / "physicsguard").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "physicsguard"\n'
        f'version = "{pyproject_version}"\n',
        encoding="utf-8",
    )
    (root / "VERSION").write_text(
        (version_file_version or pyproject_version) + "\n", encoding="utf-8"
    )
    (root / "src" / "physicsguard" / "__init__.py").write_text(
        f'__version__ = "{source_version or pyproject_version}"\n',
        encoding="utf-8",
    )


def _package_authority(
    root: Path,
    *,
    distribution_name: str,
    package_name: str,
    version: str,
) -> install_authority.PythonPackageAuthority:
    tree = install_authority.fingerprint_python_package_tree(root)
    return install_authority.PythonPackageAuthority(
        distribution_name=distribution_name,
        distribution_version=version,
        package_name=package_name,
        package_root=tree.root,
        package_tree_sha256=tree.sha256,
        package_file_count=tree.file_count,
        direct_url_sha256="sha256:direct-url",
        project_file_sha256="sha256:pyproject",
        authority_sha256="sha256:distribution-authority",
    )


def _write_package_tree(root: Path, *, marker: str = "current") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "__init__.py").write_text(f'MARKER = "{marker}"\n', encoding="utf-8")


def test_generator_marks_entire_author_control_subtree_source_only() -> None:
    skill_id = "physicsguard-ai-debugging"

    overrides = generator._content_role_overrides(skill_id)

    assert overrides[0] == {
        "path": f"skill/{skill_id}/.skillguard",
        "role": "contract_schema",
        "install_disposition": "source_only",
        "reason": "author_control_source_only",
    }
    assert overrides[1]["path"] == f"skill/{skill_id}/guard-model"
    assert overrides[1]["install_disposition"] == "source_only"


def test_suite_checks_accept_the_generator_frozen_identity_without_history_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checker = _load_suite_checker()
    identity = {
        "physicsguard_version": "0.15.2",
        "physicsguard_authority_sha256": "sha256:physicsguard-authority",
        "flowguard_version": "0.68.7",
        "flowguard_schema_version": "1.0",
        "flowguard_package_tree_sha256": "sha256:flowguard-tree",
        "flowguard_direct_url_sha256": "sha256:flowguard-direct-url",
        "flowguard_authority_sha256": "sha256:flowguard-authority",
        "skillguard_version": "0.7.2",
        "skillguard_api_tree_sha256": "sha256:skillguard-api-tree",
        "skillguard_distribution_tree_sha256": "sha256:skillguard-distribution-tree",
        "skillguard_direct_url_sha256": "sha256:skillguard-direct-url",
        "skillguard_authority_sha256": "sha256:skillguard-authority",
    }
    monkeypatch.setattr(
        checker,
        "_current_toolchain_identity_resolution",
        lambda: (identity, None),
    )

    graph = {
        "schema_version": checker.PROMPT_LOAD_GRAPH_SCHEMA,
        "suite_version": identity["physicsguard_version"],
        "toolchain_identity": identity,
    }
    graph_report = checker.check_prompt_load_graph(graph, check_files=False)
    graph_codes = {row["code"] for row in graph_report["findings"]}
    assert "toolchain_authority_unresolved" not in graph_codes
    assert "prompt_load_suite_version_stale" not in graph_codes
    assert "prompt_load_toolchain_identity_stale" not in graph_codes

    mesh = {"toolchain_identity": identity}
    mesh_report = checker.check_mesh(mesh, check_targets=False)
    mesh_codes = {row["code"] for row in mesh_report["findings"]}
    assert "toolchain_authority_unresolved" not in mesh_codes
    assert "toolchain_identity_stale" not in mesh_codes

    monkeypatch.setattr(
        checker,
        "_current_toolchain_identity_resolution",
        lambda: (
            None,
            "RuntimeError:flowguard_authority_mismatch:"
            "project=0.68.6:installed=0.68.7",
        ),
    )
    blocked = checker.check_prompt_load_graph(graph, check_files=False)
    assert "toolchain_authority_unresolved" in {
        row["code"] for row in blocked["findings"]
    }
    assert blocked["structure_status"] == "blocked"

    retired_flowguard_version = ".".join(("0", "68", "2"))
    for path in (
        SUITE_CHECKER_PATH,
        ROOT / "tests" / "test_physicsguard_skill_entry_loading.py",
        ROOT / "tests" / "test_skillguard_v2_runtime_authority_audit.py",
    ):
        assert retired_flowguard_version not in path.read_text(encoding="utf-8")


def test_generator_resolves_current_toolchain_without_version_literal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_physicsguard_versions(repository)
    project_path = repository / "project.toml"
    _write_flowguard_project(project_path, "9.8.7")
    flowguard_root = tmp_path / "flowguard"
    _write_package_tree(flowguard_root)
    flowguard_authority = _package_authority(
        flowguard_root,
        distribution_name="flowguard",
        package_name="flowguard",
        version="9.8.7",
    )
    loaded_roots: list[Path] = []
    verified_roots: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        generator.importlib,
        "import_module",
        lambda name: SimpleNamespace(SCHEMA_VERSION="1.0"),
    )
    monkeypatch.setattr(
        generator,
        "resolve_python_package_authority",
        lambda distribution_name, package_name: flowguard_authority,
    )
    monkeypatch.setattr(
        generator,
        "verify_loaded_package_modules",
        lambda package_name, root: verified_roots.append(
            (package_name, Path(root))
        ),
    )
    skillguard_tree = "sha256:skillguard-tree"
    monkeypatch.setattr(
        generator,
        "load_skillguard_consumer_api",
        lambda root: loaded_roots.append(Path(root))
        or SimpleNamespace(
            distribution_version="7.6.5",
            distribution_authority_sha256="sha256:skillguard-authority",
            distribution_direct_url_sha256="sha256:skillguard-direct-url",
            package_tree_sha256=skillguard_tree,
            distribution_package_tree_sha256=skillguard_tree,
        ),
    )
    selected_skillguard = tmp_path / "installed-skillguard"

    identity = generator.current_toolchain_identity(
        repository_root=repository,
        flowguard_project_path=project_path,
        skillguard_root=selected_skillguard,
    )

    assert identity["physicsguard_version"] == "3.2.1"
    assert identity["physicsguard_authority_sha256"].startswith("sha256:")
    assert identity["flowguard_version"] == "9.8.7"
    assert identity["flowguard_schema_version"] == "1.0"
    assert identity["flowguard_package_tree_sha256"] == (
        flowguard_authority.package_tree_sha256
    )
    assert identity["flowguard_direct_url_sha256"] == "sha256:direct-url"
    assert identity["flowguard_authority_sha256"].startswith("sha256:")
    assert identity["skillguard_version"] == "7.6.5"
    assert identity["skillguard_api_tree_sha256"] == skillguard_tree
    assert identity["skillguard_distribution_tree_sha256"] == skillguard_tree
    assert identity["skillguard_direct_url_sha256"] == (
        "sha256:skillguard-direct-url"
    )
    assert identity["skillguard_authority_sha256"] == (
        "sha256:skillguard-authority"
    )
    assert loaded_roots == [selected_skillguard]
    assert verified_roots == [("flowguard", flowguard_root.resolve())]
    source = (ROOT / "scripts" / "upgrade_purpose_contracts.py").read_text(
        encoding="utf-8"
    )
    assigned_names = {
        target.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    assert "FLOWGUARD_VERSION" not in assigned_names
    assert "SKILLGUARD_VERSION" not in assigned_names
    assert 'importlib.metadata.version("skillguard")' not in source


def test_generator_blocks_stale_flowguard_project_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_physicsguard_versions(repository)
    project_path = repository / "project.toml"
    _write_flowguard_project(project_path, "0.68.6")
    flowguard_root = tmp_path / "flowguard"
    _write_package_tree(flowguard_root)
    flowguard_authority = _package_authority(
        flowguard_root,
        distribution_name="flowguard",
        package_name="flowguard",
        version="0.68.7",
    )
    monkeypatch.setattr(
        generator.importlib,
        "import_module",
        lambda name: SimpleNamespace(SCHEMA_VERSION="1.0"),
    )
    monkeypatch.setattr(
        generator,
        "resolve_python_package_authority",
        lambda distribution_name, package_name: flowguard_authority,
    )
    monkeypatch.setattr(
        generator,
        "verify_loaded_package_modules",
        lambda package_name, root: None,
    )

    with pytest.raises(RuntimeError, match="flowguard_authority_mismatch"):
        generator.current_toolchain_identity(
            repository_root=repository,
            flowguard_project_path=project_path,
            skillguard_root=tmp_path / "unused",
        )


def test_generator_blocks_physicsguard_version_drift_before_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_physicsguard_versions(
        repository,
        pyproject_version="3.2.1",
        version_file_version="3.2.0",
        source_version="3.2.1",
    )
    flowguard_path = repository / ".flowguard" / "project.toml"
    flowguard_path.parent.mkdir()
    _write_flowguard_project(flowguard_path, "9.8.7")
    for skill_id in generator.TARGETS:
        control = repository / "skill" / skill_id / ".skillguard"
        control.mkdir(parents=True)
        (control / "contract-source.json").write_text("{}\n", encoding="utf-8")
    formal_output = repository / ".skillguard" / "test-mesh.json"
    formal_output.parent.mkdir()
    formal_output.write_bytes(b"original-managed-bytes\n")
    called = False

    def unexpected_transaction(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("transaction must not start")

    monkeypatch.setattr(generator, "_run_generation_transaction", unexpected_transaction)

    with pytest.raises(RuntimeError, match="physicsguard_version_authority_mismatch"):
        generator.main(repository)

    assert called is False
    assert formal_output.read_bytes() == b"original-managed-bytes\n"


def test_generator_freezes_identity_once_and_passes_same_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    for skill_id in generator.TARGETS:
        control = repository / "skill" / skill_id / ".skillguard"
        control.mkdir(parents=True)
        (control / "contract-source.json").write_text("{}\n", encoding="utf-8")
    identity = {
        "physicsguard_version": "3.2.1",
        "flowguard_schema_version": "1.0",
        "frozen": "one-snapshot",
    }
    calls = 0
    consumed: list[dict[str, str]] = []

    def freeze(**_kwargs):
        nonlocal calls
        calls += 1
        return identity

    monkeypatch.setattr(generator, "current_toolchain_identity", freeze)
    monkeypatch.setattr(
        generator,
        "_run_generation_transaction",
        lambda root, frozen: consumed.append(frozen),
    )

    assert generator.main(repository) == 0

    assert calls == 1
    assert consumed == [identity]
    assert json.loads(capsys.readouterr().out)["status"] == "pass"


def test_generation_stage_failure_on_sixth_member_leaves_managed_bytes_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    for skill_id in generator.TARGETS:
        prompt = repository / "skill" / skill_id / "SKILL.md"
        prompt.parent.mkdir(parents=True)
        prompt.write_bytes(f"original:{skill_id}\n".encode("utf-8"))
    before = {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    call_count = 0

    def fail_on_sixth(
        skill_id: str,
        _config: dict[str, object],
        _identity: dict[str, str],
    ) -> None:
        nonlocal call_count
        call_count += 1
        (generator.SKILL_ROOT / skill_id / "SKILL.md").write_text(
            f"staged:{skill_id}\n", encoding="utf-8"
        )
        if call_count == 6:
            raise RuntimeError("fixture-sixth-member-failure")

    monkeypatch.setattr(generator, "_write_unit_test_mesh_manifest", lambda: None)
    monkeypatch.setattr(generator, "upgrade_target_current", fail_on_sixth)
    monkeypatch.setattr(generator, "_write_prompt_load_graph", lambda _identity: None)
    monkeypatch.setattr(generator, "_update_suite_mesh", lambda _identity: None)
    monkeypatch.setattr(
        generator, "_update_model_regression_manifest", lambda _identity: None
    )

    with pytest.raises(RuntimeError, match="fixture-sixth-member-failure"):
        generator._run_generation_transaction(
            repository,
            {
                "physicsguard_version": "3.2.1",
                "flowguard_schema_version": "1.0",
            },
        )

    after = {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    assert call_count == 6
    assert after == before


def test_package_tree_fingerprint_ignores_cache_but_covers_all_source_bytes(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first" / "skillguard_v2"
    second = tmp_path / "second" / "skillguard_v2"
    for root in (first, second):
        _write_package_tree(root)
        (root / "consumer_distribution.py").write_text(
            "VALUE = 1\n", encoding="utf-8"
        )
        cache = root / "__pycache__"
        cache.mkdir()
    (first / "__pycache__" / "one.pyc").write_bytes(b"first-cache")
    (second / "__pycache__" / "two.pyc").write_bytes(b"second-cache")

    first_tree = install_authority.fingerprint_python_package_tree(first)
    second_tree = install_authority.fingerprint_python_package_tree(second)

    assert first_tree.files == second_tree.files
    assert first_tree.sha256 == second_tree.sha256
    (second / "consumer_distribution.py").write_text(
        "VALUE = 2\n", encoding="utf-8"
    )
    assert (
        install_authority.fingerprint_python_package_tree(second).sha256
        != first_tree.sha256
    )


def test_distribution_authority_binds_editable_metadata_direct_url_and_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "flowguard-source"
    package_root = source_root / "flowguard"
    _write_package_tree(package_root)
    (package_root / "model.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source_root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "flowguard"\n'
        'version = "9.8.7"\n\n'
        "[tool.setuptools.packages.find]\n"
        'include = ["flowguard*"]\n',
        encoding="utf-8",
    )

    class FakeDistribution:
        metadata = {"Name": "flowguard"}
        version = "9.8.7"
        files = None

        @staticmethod
        def read_text(name: str) -> str | None:
            if name != "direct_url.json":
                return None
            return json.dumps(
                {
                    "dir_info": {"editable": True},
                    "url": source_root.resolve().as_uri(),
                }
            )

    monkeypatch.setattr(
        install_authority.importlib.metadata,
        "distribution",
        lambda name: FakeDistribution(),
    )

    authority = install_authority.resolve_python_package_authority(
        "flowguard", "flowguard"
    )

    assert authority.distribution_version == "9.8.7"
    assert authority.package_root == package_root.resolve()
    assert authority.package_file_count == 2
    assert authority.direct_url_sha256 is not None
    assert authority.project_file_sha256 is not None
    assert authority.authority_sha256.startswith("sha256:")


def test_skillguard_loader_blocks_distribution_tree_drift_before_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "installed-skillguard"
    installed_package = installed_root / "scripts" / "skillguard_v2"
    distribution_package = tmp_path / "distribution" / "skillguard_v2"
    for package in (installed_package, distribution_package):
        _write_package_tree(package)
        (package / "consumer_distribution.py").write_text(
            "def consumer_distribution_plan(*args, **kwargs):\n"
            "    return {}\n\n"
            "def audit_consumer_distribution(*args, **kwargs):\n"
            "    return {}\n",
            encoding="utf-8",
        )
    (distribution_package / "unrelated-extra-owner.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    authority = _package_authority(
        distribution_package,
        distribution_name="skillguard",
        package_name="skillguard_v2",
        version="7.6.5",
    )
    monkeypatch.setattr(
        install_authority,
        "resolve_python_package_authority",
        lambda distribution_name, package_name: authority,
    )

    with pytest.raises(
        install_authority.SkillGuardAuthorityUnavailable,
        match="skillguard_installed_distribution_tree_mismatch",
    ):
        install_authority.load_skillguard_consumer_api(installed_root)


def test_skillguard_loader_binds_installed_and_distribution_trees(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "installed-skillguard"
    installed_package = installed_root / "scripts" / "skillguard_v2"
    distribution_package = tmp_path / "distribution" / "skillguard_v2"
    for package in (installed_package, distribution_package):
        _write_package_tree(package)
        (package / "consumer_distribution.py").write_text(
            "def consumer_distribution_plan(*args, **kwargs):\n"
            "    return {}\n\n"
            "def audit_consumer_distribution(*args, **kwargs):\n"
            "    return {}\n",
            encoding="utf-8",
        )
    authority = _package_authority(
        distribution_package,
        distribution_name="skillguard",
        package_name="skillguard_v2",
        version="7.6.5",
    )
    monkeypatch.setattr(
        install_authority,
        "resolve_python_package_authority",
        lambda distribution_name, package_name: authority,
    )
    saved_modules = {
        name: module
        for name, module in tuple(sys.modules.items())
        if name == "skillguard_v2" or name.startswith("skillguard_v2.")
    }
    for name in saved_modules:
        sys.modules.pop(name, None)
    try:
        api = install_authority.load_skillguard_consumer_api(installed_root)
    finally:
        for name in tuple(sys.modules):
            if name == "skillguard_v2" or name.startswith("skillguard_v2."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)

    assert api.distribution_version == "7.6.5"
    assert api.package_tree_sha256 == api.distribution_package_tree_sha256
    assert api.package_file_count == 2
    assert api.distribution_authority_sha256 == authority.authority_sha256


def test_skillguard_loader_blocks_foreign_loaded_submodule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "installed-skillguard"
    installed_package = installed_root / "scripts" / "skillguard_v2"
    distribution_package = tmp_path / "distribution" / "skillguard_v2"
    for package in (installed_package, distribution_package):
        _write_package_tree(package)
        (package / "consumer_distribution.py").write_text(
            "def consumer_distribution_plan(*args, **kwargs):\n"
            "    return {}\n\n"
            "def audit_consumer_distribution(*args, **kwargs):\n"
            "    return {}\n",
            encoding="utf-8",
        )
    authority = _package_authority(
        distribution_package,
        distribution_name="skillguard",
        package_name="skillguard_v2",
        version="7.6.5",
    )
    monkeypatch.setattr(
        install_authority,
        "resolve_python_package_authority",
        lambda distribution_name, package_name: authority,
    )
    saved_modules = {
        name: module
        for name, module in tuple(sys.modules.items())
        if name == "skillguard_v2" or name.startswith("skillguard_v2.")
    }
    for name in saved_modules:
        sys.modules.pop(name, None)
    foreign_path = tmp_path / "foreign.py"
    foreign_path.write_text("VALUE = 1\n", encoding="utf-8")
    foreign = ModuleType("skillguard_v2.foreign")
    foreign.__file__ = str(foreign_path)
    sys.modules[foreign.__name__] = foreign
    try:
        with pytest.raises(
            install_authority.SkillGuardAuthorityUnavailable,
            match="package_loaded_module_owner_mismatch",
        ):
            install_authority.load_skillguard_consumer_api(installed_root)
    finally:
        for name in tuple(sys.modules):
            if name == "skillguard_v2" or name.startswith("skillguard_v2."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
