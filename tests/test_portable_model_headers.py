from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_header_script() -> ModuleType:
    path = ROOT / "scripts" / "portable_model_headers.py"
    spec = importlib.util.spec_from_file_location("portable_model_headers", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_example_yaml_files_have_portable_headers() -> None:
    headers = _load_header_script()
    files = headers.tracked_example_yaml_files(ROOT)

    assert files
    missing = [str(path.relative_to(ROOT)) for path in files if not headers.has_portable_header(path)]
    assert missing == []


def test_committed_example_yaml_files_still_parse_after_headers() -> None:
    headers = _load_header_script()

    for path in headers.tracked_example_yaml_files(ROOT):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
