"""Loaders for test-file contracts and related artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.parameter_coverage import (
    CoveragePolicySpec,
    ParameterCatalogSpec,
    ParameterMappingEdgesSpec,
    ParameterRoleMatrixSpec,
)
from physicsguard.schema.test_file_contract import (
    ExtractorProfileSpec,
    ModelBindingSpec,
    TestBenchProfileSpec,
    TestFileContractSpec,
    TestFileProjectIndexSpec,
)


SpecT = TypeVar("SpecT", bound=BaseModel)


def load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {yaml_path}: {exc}") from exc
    if data is None:
        raise ValueError(f"YAML file is empty: {yaml_path}")
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {yaml_path}")
    return data


def load_spec(path: str | Path, spec_type: type[SpecT]) -> SpecT:
    yaml_path = Path(path)
    data = load_yaml_mapping(yaml_path)
    try:
        return spec_type.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid {spec_type.__name__} in {yaml_path}: {exc}") from exc


def load_data_file_manifest(path: str | Path) -> DataFileManifestSpec:
    return load_spec(path, DataFileManifestSpec)


def load_testbench_profile(path: str | Path) -> TestBenchProfileSpec:
    return load_spec(path, TestBenchProfileSpec)


def load_extractor_profile(path: str | Path) -> ExtractorProfileSpec:
    return load_spec(path, ExtractorProfileSpec)


def load_model_binding(path: str | Path) -> ModelBindingSpec:
    return load_spec(path, ModelBindingSpec)


def load_parameter_catalog(path: str | Path) -> ParameterCatalogSpec:
    return load_spec(path, ParameterCatalogSpec)


def load_parameter_role_matrix(path: str | Path) -> ParameterRoleMatrixSpec:
    return load_spec(path, ParameterRoleMatrixSpec)


def load_parameter_mapping_edges(path: str | Path) -> ParameterMappingEdgesSpec:
    return load_spec(path, ParameterMappingEdgesSpec)


def load_coverage_policy(path: str | Path) -> CoveragePolicySpec:
    return load_spec(path, CoveragePolicySpec)


def load_test_file_contract(path: str | Path) -> TestFileContractSpec:
    return load_spec(path, TestFileContractSpec)


def load_test_file_project_index(path: str | Path) -> TestFileProjectIndexSpec:
    return load_spec(path, TestFileProjectIndexSpec)


__all__ = [
    "load_coverage_policy",
    "load_data_file_manifest",
    "load_extractor_profile",
    "load_model_binding",
    "load_parameter_catalog",
    "load_parameter_mapping_edges",
    "load_parameter_role_matrix",
    "load_spec",
    "load_test_file_contract",
    "load_test_file_project_index",
    "load_testbench_profile",
    "load_yaml_mapping",
]
