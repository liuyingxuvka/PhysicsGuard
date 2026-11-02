"""The model-format reference says exactly which rows and readings the tool checks; these tests hold it to that.

Each example below is quoted from skill/physicsguard/references/model-format.md and run through the loader, so a
claim the code does not keep (or a rule the reference leaves out) fails here.
"""
from __future__ import annotations

import re

import pytest

from conftest import ROOT
from test_derived_unit_conversions import WATER, _load, _write

REFERENCE = (ROOT / "skill" / "physicsguard" / "references" / "model-format.md").read_text(encoding="utf-8")


def _quoted(sentence_start: str, sentence_end: str) -> list[str]:
    start = REFERENCE.index(sentence_start)
    return re.findall(r"`([^`]+)`", REFERENCE[start:REFERENCE.index(sentence_end, start)])


def test_every_spelling_the_reference_lists_is_read_as_it_says() -> None:
    from physicsguard.core.units import known_conversion

    spellings = _quoted("So `l/min`", " are read as ")
    assert len(spellings) >= 9
    for spelling in spellings:
        target = "kg/s" if spelling.startswith("kg") else "L/min"
        assert known_conversion(spelling, target) == pytest.approx((1.0, 0.0)), spelling


def test_a_space_without_a_power_is_not_read_as_the_reference_says() -> None:
    from physicsguard.core.units import read_unit

    assert "`L min` is not read" in REFERENCE
    assert read_unit("L min") is None and read_unit("L min^-1") is not None


def test_the_separators_allowed_between_whole_readings_are_the_ones_the_reference_names() -> None:
    from physicsguard.schema.observed_conversion import WHOLE_SIGNAL_SEPARATORS, _signal_readings

    named = _quoted("with only\n  brackets, commas", " between them")
    assert sorted(set("".join(named)) | set("()[],")) == sorted(WHOLE_SIGNAL_SEPARATORS)
    for separator in WHOLE_SIGNAL_SEPARATORS:
        assert _signal_readings(f"6 L/min {separator} 0.1 kg/s").whole, separator
    for other in ("~", "about", "or"):
        assert not _signal_readings(f"6 L/min {other} 0.1 kg/s").whole, other


@pytest.mark.parametrize("signal, row, outcome", [
    ("6 gallons/min", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 L fortnight^-1", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 L", {"value": 0.1}, "conversion_unchecked"),
    ("6 L/min = 6 kg/s", {"value": 6.0}, "refused"),
    ("6 L/min (0.1 kg/s)", {"value": 0.1}, "checked"),
    ("AI outlet temperature 33 C", {"value": 300.0, "unit": "K"}, "signal_reading_disagrees"),
    ("AI heater power", {"value": 6.0}, "not flagged"),
    ("valve 2 open", {"value": 6.0}, "not flagged"),
    ("T_tank_C@70", {"value": 6.0}, "not flagged"),
])
def test_the_reference_examples_behave_as_it_says(tmp_path, signal, row, outcome) -> None:
    assert f"`{signal}`" in REFERENCE, f"{signal} is no longer an example in the reference"
    path = _write(tmp_path, {"heater.x": {"unit": "kg/s", **row, "external_signal": signal}}, WATER)
    if outcome == "refused":
        with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.x"):
            _load(path)
        return
    loaded = _load(path).variables["heater.x"]
    flags = {"signal_reading_unreadable": loaded._signal_unreadable, "signal_reading_disagrees": loaded._signal_disagrees,
             "conversion_unchecked": loaded._conversion_checked is False and not loaded._signal_disagrees}
    if outcome == "checked":
        assert loaded._conversion_checked is True and not any(flags.values())
    elif outcome == "not flagged":
        assert loaded._conversion_checked is None and not any(flags.values())
    else:
        assert [name for name, raised in flags.items() if raised] == [outcome]
