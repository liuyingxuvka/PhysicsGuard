from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    fingerprint_blueprint,
)
from physicsguard.io.physical_model_blueprint_loader import load_physical_model_blueprint


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "physical_model_blueprint"
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "physical_model_blueprint.yaml"


def test_complete_external_physical_blueprint_is_strict_and_canonical(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()

    assert blueprint.qualification_target == "external_physical_target"
    assert blueprint.artifact_root == "blueprint_directory"
    assert blueprint.target.target_kind == "physical_system"
    assert len([item for item in blueprint.elements if item.parent_id is None]) == 1
    assert fingerprint_blueprint(blueprint) == fingerprint_blueprint(blueprint.model_dump(mode="json"))


def test_canonical_identity_ignores_set_like_input_order(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    reordered = blueprint.model_dump(mode="json")
    for key in ("providers", "elements", "ports", "semantics", "validity_boundaries", "bindings"):
        reordered[key] = list(reversed(reordered[key]))
    reordered["inventory"]["members"] = list(reversed(reordered["inventory"]["members"]))

    assert fingerprint_blueprint(PhysicalModelBlueprint.model_validate(reordered)) == fingerprint_blueprint(blueprint)


def test_caller_cannot_self_declare_blueprint_ready(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = blueprint.model_dump(mode="json")
    data["ready"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PhysicalModelBlueprint.model_validate(data)


def test_artifact_root_is_explicit_and_has_one_meaning(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    missing = blueprint.model_dump(mode="json")
    del missing["artifact_root"]
    with pytest.raises(ValidationError, match="artifact_root"):
        PhysicalModelBlueprint.model_validate(missing)

    alternate = blueprint.model_dump(mode="json")
    alternate["artifact_root"] = "repository_root"
    with pytest.raises(ValidationError, match="blueprint_directory"):
        PhysicalModelBlueprint.model_validate(alternate)


def test_physicsguard_software_is_not_a_physical_qualification_target(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = blueprint.model_dump(mode="json")
    data["target"]["target_kind"] = "software"

    with pytest.raises(ValidationError, match="Input should be"):
        PhysicalModelBlueprint.model_validate(data)


def test_multiple_roots_and_duplicate_primary_owners_are_contract_errors(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    two_roots = blueprint.model_dump(mode="json")
    pipe = next(item for item in two_roots["elements"] if item["element_id"] == "pipe")
    pipe["parent_id"] = None
    pipe["depth"] = 0

    with pytest.raises(ValidationError, match="exactly one root"):
        PhysicalModelBlueprint.model_validate(two_roots)

    duplicate_owner = deepcopy(blueprint.model_dump(mode="json"))
    pump = next(item for item in duplicate_owner["elements"] if item["element_id"] == "pump")
    pipe = next(item for item in duplicate_owner["elements"] if item["element_id"] == "pipe")
    pipe["owned_behavior_ids"].append(pump["owned_behavior_ids"][0])
    with pytest.raises(ValidationError, match="duplicate primary owners"):
        PhysicalModelBlueprint.model_validate(duplicate_owner)


def test_local_artifact_path_cannot_escape_boundary(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = blueprint.model_dump(mode="json")
    data["bindings"][0]["artifact"]["repo_path"] = "../outside.txt"

    with pytest.raises(ValidationError, match="remain relative"):
        PhysicalModelBlueprint.model_validate(data)


def test_checked_in_yaml_and_json_fixtures_are_one_canonical_logical_object() -> None:
    yaml_blueprint = load_physical_model_blueprint(FIXTURE_ROOT / "canonical_minimal.yaml")
    json_blueprint = load_physical_model_blueprint(FIXTURE_ROOT / "canonical_minimal.json")

    assert yaml_blueprint == json_blueprint
    assert fingerprint_blueprint(yaml_blueprint) == fingerprint_blueprint(json_blueprint)


def test_checked_in_template_is_valid_and_matches_the_canonical_example() -> None:
    template = load_physical_model_blueprint(TEMPLATE_PATH)
    canonical = load_physical_model_blueprint(FIXTURE_ROOT / "canonical_minimal.yaml")

    assert template == canonical
    assert fingerprint_blueprint(template) == fingerprint_blueprint(canonical)
