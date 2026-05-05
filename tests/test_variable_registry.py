from __future__ import annotations

import numpy as np
import pytest

from physicsguard.core.registry import VariableRecord, VariableRegistry


def record(name: str = "a.x") -> VariableRecord:
    return VariableRecord(
        name=name,
        unit="1",
        lower_bound=-1.0,
        upper_bound=1.0,
        initial_guess=0.0,
        scale=1.0,
    )


def test_add_and_retrieve_variable() -> None:
    registry = VariableRegistry()
    assert registry.add_variable(record()) == 0
    assert registry.get_index("a.x") == 0
    assert registry.get_record("a.x").unit == "1"
    assert registry.get_record("a.x").local_name == "x"


def test_duplicate_variable_fails() -> None:
    registry = VariableRegistry()
    registry.add_variable(record())
    with pytest.raises(ValueError, match="duplicate"):
        registry.add_variable(record())


def test_missing_lookup_fails() -> None:
    registry = VariableRegistry()
    with pytest.raises(KeyError, match="unknown variable"):
        registry.get_index("missing.x")


def test_invalid_bounds_fail() -> None:
    with pytest.raises(ValueError, match="lower_bound"):
        VariableRecord("a.x", None, 1.0, 1.0, 1.0, 1.0)


def test_initial_guess_outside_bounds_fails() -> None:
    with pytest.raises(ValueError, match="initial_guess"):
        VariableRecord("a.x", None, 0.0, 1.0, 2.0, 1.0)


def test_scale_nonpositive_fails() -> None:
    with pytest.raises(ValueError, match="scale"):
        VariableRecord("a.x", None, 0.0, 1.0, 0.5, 0.0)


def test_variable_name_must_be_fully_qualified() -> None:
    with pytest.raises(ValueError, match="fully qualified"):
        VariableRecord("x", None, 0.0, 1.0, 0.5, 1.0)


def test_local_name_must_be_unqualified() -> None:
    with pytest.raises(ValueError, match="unqualified"):
        VariableRecord("a.x", None, 0.0, 1.0, 0.5, 1.0, local_name="a.x")


def test_source_component_must_match_qualified_name() -> None:
    with pytest.raises(ValueError, match="source_component"):
        VariableRecord(
            "a.x",
            None,
            0.0,
            1.0,
            0.5,
            1.0,
            source_component="b",
            local_name="x",
        )


def test_vector_to_dict_validates_length() -> None:
    registry = VariableRegistry()
    registry.add_variable(record())
    with pytest.raises(ValueError, match="length"):
        registry.vector_to_dict(np.array([1.0, 2.0]))


def test_dict_to_vector_requires_all_names() -> None:
    registry = VariableRegistry()
    registry.add_variable(record("a.x"))
    registry.add_variable(record("b.x"))
    with pytest.raises(KeyError, match="missing"):
        registry.dict_to_vector({"a.x": 1.0})
