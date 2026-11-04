"""The model-format reference says exactly which rows and readings the tool checks; these tests hold it to that.

Each example below is quoted from skill/physicsguard/references/model-format.md and run through the loader, so a
claim the code does not keep (or a rule the reference leaves out) fails here.
"""
from __future__ import annotations

import re

import pytest
import yaml

from conftest import ROOT, run_cli
from test_derived_unit_conversions import SHOWER, WATER, _load, _write

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


@pytest.mark.parametrize("separator", [",", ";", ":", "=", "(", ")", "[", "]"])
def test_the_reference_delimiters_keep_adjacent_readings_separate(tmp_path, separator) -> None:
    assert f"`{separator}`" in REFERENCE
    path = _write(tmp_path, {"heater.x": {"value": 0.1, "unit": "kg/s",
                                          "external_signal": f"6 L/min{separator}0.1 kg/s"}}, WATER)
    row = _load(path).variables["heater.x"]
    assert row._conversion_checked is True and not row._signal_unreadable
    assert "6 L/min" in row._conversion_check and "0.1 kg/s" in row._conversion_check


@pytest.mark.parametrize("signal, row, outcome", [
    ("6 gallons/min", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 gpm", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 gallons", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 °X", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 L fortnight^-1", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 L a fortnight", {"value": 6.0}, "signal_reading_unreadable"),
    ("6 L", {"value": 0.1}, "conversion_unchecked"),
    ("6 L/min = 6 kg/s", {"value": 6.0}, "refused"),
    ("6 L/min (0.1 kg/s)", {"value": 0.1}, "checked"),
    ("AI outlet temperature 33 C", {"value": 300.0, "unit": "K"}, "refused"),
    ("AI heater power", {"value": 6.0}, "not flagged"),
    ("valve 2 open", {"value": 6.0}, "signal_reading_unreadable"),
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


@pytest.mark.parametrize("readme", ["README.md", "README.zh-CN.md"])
def test_the_readme_shower_walkthrough_matches_both_printed_verdicts(tmp_path, readme) -> None:
    text = (ROOT / readme).read_text(encoding="utf-8")
    examples = re.findall(r"```console\n\$ python -m physicsguard\.cli hierarchy evaluate [^\n]+\n(.*?)```", text, re.S)
    assert len(examples) >= 2
    before = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(SHOWER / "observed_ai.yaml"))
    assert before.returncode == 1 and not before.stderr
    assert before.stdout.strip() == examples[0].strip()

    # Apply exactly the two field values named in each walkthrough; keep the external evidence consistent.
    correction = re.search(r"`raw_value: ([^`]+)`.*?`external_signal: ([^`]+)`", text, re.S)
    assert correction is not None
    data = yaml.safe_load((SHOWER / "observed_ai.yaml").read_text(encoding="utf-8"))
    row = data["variables"]["mix.T_out_K"]
    row["raw_value"] = float(correction.group(1))
    row["external_signal"] = correction.group(2)
    corrected = tmp_path / "observed_ai.yaml"
    corrected.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    after = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(corrected))
    assert after.returncode == 0 and not after.stderr
    assert after.stdout.strip() == examples[1].strip()


def test_the_readme_correction_cannot_leave_the_previous_external_reading(tmp_path) -> None:
    data = yaml.safe_load((SHOWER / "observed_ai.yaml").read_text(encoding="utf-8"))
    data["variables"]["mix.T_out_K"]["raw_value"] = 33.0
    corrected = tmp_path / "stale_signal.yaml"
    corrected.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(corrected))
    assert result.returncode == 2
    assert "signal_reading_disagrees:mix.T_out_K" in result.stderr
