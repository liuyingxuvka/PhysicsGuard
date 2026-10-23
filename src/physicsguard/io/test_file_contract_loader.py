"""Loaders for test-file contracts and related artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.model_dataset_validation import ModelValidationPlanSpec
from physicsguard.schema.test_file_contract import (
    TestFileContractSpec,
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


def load_model_validation_plan(path: str | Path) -> ModelValidationPlanSpec:
    return load_spec(path, ModelValidationPlanSpec)


def load_test_file_contract(path: str | Path) -> TestFileContractSpec:
    return load_spec(path, TestFileContractSpec)


__all__ = [
    "load_data_file_manifest",
    "load_model_validation_plan",
    "load_spec",
    "load_test_file_contract",
    "load_yaml_mapping",
]
