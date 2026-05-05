from __future__ import annotations

from physicsguard.core.hierarchy import BlockIndex
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.schema.hierarchy_spec import HierarchySpec
from physicsguard.schema.system_spec import SystemSpec


def system() -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": "block_index_system",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
                {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            ],
            "connections": [{"from_variable": "a.x", "to_variable": "b.x"}],
            "boundaries": [{"variable": "a.x", "value": 1.0}],
        }
    )


def hierarchy() -> HierarchySpec:
    return HierarchySpec.model_validate(
        {
            "blocks": [
                {"id": "root", "level": 0},
                {"id": "left", "level": 1, "parent_id": "root", "components": ["a"]},
                {"id": "right", "level": 1, "parent_id": "root", "components": ["b"]},
            ]
        }
    )


def test_component_to_block_mapping_and_traversal() -> None:
    index = BlockIndex(hierarchy(), system())
    assert index.component_block("a") == "left"
    assert [block.id for block in index.children("root")] == ["left", "right"]
    assert index.parent("left").id == "root"
    assert [block.id for block in index.ancestors("left")] == ["root"]
    assert [block.id for block in index.descendants("root")] == ["left", "right"]


def test_residual_assignment_to_component_block() -> None:
    index = BlockIndex(hierarchy(), system())
    record = ResidualRecord(
        name="a.dummy_target",
        value=0.0,
        scale=1.0,
        source="a",
        role="equation",
        diagnostic_key="dummy_target_mismatch",
    )
    assert index.block_for_residual(record) == "left"


def test_boundary_residual_assignment_to_component_block() -> None:
    index = BlockIndex(hierarchy(), system())
    record = ResidualRecord(
        name="boundary:a.x",
        value=0.0,
        scale=1.0,
        source="boundary",
        role="boundary",
        diagnostic_key="boundary_mismatch",
    )
    assert index.block_for_residual(record) == "left"


def test_connection_between_child_blocks_assigns_to_parent() -> None:
    spec = system()
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    records = builder.diagnostic_residual_records(registry.initial_vector())
    connection = next(record for record in records if record.role == "connection")
    assert BlockIndex(hierarchy(), spec).block_for_residual(connection) == "root"


def test_connection_inside_same_block_assigns_to_that_block() -> None:
    spec = system()
    same_block = HierarchySpec.model_validate({"blocks": [{"id": "both", "level": 0, "components": ["a", "b"]}]})
    builder = ResidualBuilder(spec)
    connection = next(record for record in builder.diagnostic_residual_records(builder.build_registry().initial_vector()) if record.role == "connection")
    assert BlockIndex(same_block, spec).block_for_residual(connection) == "both"


def test_unassigned_residuals_are_reported() -> None:
    index = BlockIndex(hierarchy(), system())
    record = ResidualRecord(
        name="external.residual",
        value=1.0,
        scale=1.0,
        source="external",
        role="equation",
        diagnostic_key="external_mismatch",
    )
    assignment = index.assignment_for_residual(record)
    assert assignment.block_id is None
    assert assignment.reason == "unassigned"
