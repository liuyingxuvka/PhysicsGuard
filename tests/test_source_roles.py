"""Physical inlet pairing: real source spans, native mixing and honest coverage."""
from pathlib import Path
import shutil

import pytest
import yaml

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from test_source_reading import evaluate, _parameter_only_report

FIXTURES = Path(__file__).parent / "fixtures/source_reading/second"


def run_case(tmp_path, values, question=None):
    for name in ("audit_mix.yaml", "question_mix.txt"):
        shutil.copyfile(FIXTURES / name, tmp_path / name)
    if question is not None:
        (tmp_path / "question_mix.txt").write_text(question, encoding="utf-8")
    path = tmp_path / "values.yaml"
    path.write_text(yaml.safe_dump(values), encoding="utf-8")
    runner = HierarchicalAuditRunner(load_hierarchical_audit_spec(tmp_path / "audit_mix.yaml"))
    return runner.to_dict(runner.evaluate_observed(load_observed_values(path), skip_unobserved=True))


def mixing_values():
    return yaml.safe_load((FIXTURES / "mix_range.yaml").read_text(encoding="utf-8"))


def rows(report):
    return {row["id"]: row for row in report["metadata"]["source_readings"]}


def merge(report):
    return next(row for row in report["block_verdicts"] if row["block_id"] == "merge")


def test_mixing_port_cannot_join_readings_from_different_inlets():
    _, _, report = evaluate("second", "mix_swap")
    assert report["audit_pass"] is False
    assert merge(report)["colour"] == "red"
    assert rows(report)["mix.m_dot_1_kg_s"]["colour"] == "red"
    assert "source_role_disagrees" in rows(report)["mix.m_dot_1_kg_s"]["reason"]
    assert rows(report)["claim:0"]["colour"] == "red"


@pytest.mark.parametrize("verb", ["brings", "carries", "supplies"])
def test_correct_inlet_pair_is_source_bound_and_still_computable(tmp_path, verb):
    question = (FIXTURES / "question_mix.txt").read_text(encoding="utf-8").replace("brings", verb)
    values = mixing_values()
    for row in values["variables"].values():
        if "quote" in row:
            row["quote"]["text"] = row["quote"]["text"].replace("brings", verb)
    report = run_case(tmp_path, values, question)
    assert report["audit_pass"]
    assert merge(report)["colour"] == "green"
    assert rows(report)["mix.m_dot_1_kg_s"]["source_entity"] == "Inlet A"
    assert rows(report)["mix.T_1_K"]["source_entity"] == "Inlet A"
    assert rows(report)["mix.T_1_K"]["input_group"] == "mix.inlet_1"
    assert "mix.T_out_K" in merge(report)["source_coverage"]["other_variable_dependencies"]
    # A computed/claimed answer does not need an external source quote.
    assert rows(report)["mix.T_out_K"]["colour"] == "grey"


def test_swapping_two_whole_inlet_pairs_is_not_a_role_error(tmp_path):
    values = mixing_values()
    for first, second in (("mix.m_dot_1_kg_s", "mix.m_dot_2_kg_s"), ("mix.T_1_K", "mix.T_2_K")):
        values["variables"][first], values["variables"][second] = values["variables"][second], values["variables"][first]
    report = run_case(tmp_path, values)
    assert report["audit_pass"]
    assert merge(report)["colour"] == "green"
    assert rows(report)["mix.T_1_K"]["source_entity"] == "Inlet B"


def test_one_source_inlet_cannot_be_counted_as_two(tmp_path):
    values = mixing_values()
    variables = values["variables"]
    variables["mix.m_dot_2_kg_s"] = dict(variables["mix.m_dot_1_kg_s"])
    variables["mix.T_2_K"] = dict(variables["mix.T_1_K"])
    variables["mix.m_dot_out_kg_s"]["value"] = 1 / 6
    variables["mix.T_out_K"]["value"] = 343.15
    report = run_case(tmp_path, values)
    assert report["audit_pass"] is False
    assert merge(report)["colour"] == "red"
    assert "same source inlet" in rows(report)["mix.T_2_K"]["reason"]


@pytest.mark.parametrize("question", [
    "Stream A has 5 L/min at 70 °C. Stream B has 6 L/min at 10–12 °C. water: 1 kg/L",
    "Inlet A brings 5 L/min of water at 70 °C. Inlet B brings 6 L/min of water at 70 °C. water: 1 kg/L",
])
def test_outside_or_ambiguous_binding_stays_grey_without_blocking_calculation(tmp_path, question):
    values = mixing_values()
    values["claims"] = []
    variables = values["variables"]
    if question.startswith("Stream"):
        variables["mix.m_dot_1_kg_s"]["quote"]["text"] = "5 L/min"
        variables["mix.m_dot_2_kg_s"]["quote"]["text"] = "6 L/min"
    else:
        variables["mix.T_2_K"].update(raw_value=70, external_signal="70 °C", quote={"from": "question", "text": "at 70 °C"})
        variables["mix.T_out_K"]["value"] = 343.15
    report = run_case(tmp_path, values, question)
    assert report["audit_pass"]
    assert merge(report)["colour"] == "grey"
    assert any("source role unchecked" in row["reason"] for row in rows(report).values())


def test_source_change_is_rechecked_instead_of_reusing_the_old_role(tmp_path):
    values = mixing_values()
    good = run_case(tmp_path, values)
    question = (FIXTURES / "question_mix.txt").read_text(encoding="utf-8")
    changed = question.replace("at 70 °C", "at __TEMP__").replace("at 10–12 °C", "at 70 °C").replace("__TEMP__", "10–12 °C")
    again = run_case(tmp_path, values, changed)
    assert good["audit_pass"] and not again["audit_pass"]
    assert rows(good)["mix.T_1_K"]["source_digest"] != rows(again)["mix.T_1_K"]["source_digest"]
    assert "source_role_disagrees" in rows(again)["mix.T_1_K"]["reason"]


def test_cross_document_inlet_identity_is_not_guessed(tmp_path):
    values = mixing_values()
    values["sources"]["other"] = "other.txt"
    (tmp_path / "other.txt").write_text((FIXTURES / "question_mix.txt").read_text(encoding="utf-8"), encoding="utf-8")
    values["variables"]["mix.T_1_K"]["quote"]["from"] = "other"
    report = run_case(tmp_path, values)
    assert report["audit_pass"]
    assert merge(report)["colour"] == "grey"
    assert "across source files" in rows(report)["mix.T_1_K"]["reason"]


def test_quote_repeated_outside_an_inlet_is_not_silently_attributed_to_it(tmp_path):
    question = (FIXTURES / "question_mix.txt").read_text(encoding="utf-8") + "\nA different sensor also is at 70 °C.\n"
    report = run_case(tmp_path, mixing_values(), question)
    assert report["audit_pass"]
    assert merge(report)["colour"] == "grey"
    assert rows(report)["mix.T_1_K"]["colour"] == "grey"


def test_explicit_table_row_binds_flow_and_temperature(tmp_path):
    values = mixing_values()
    values["sources"]["table"] = "inlets.md"
    (tmp_path / "inlets.md").write_text(
        "| Inlet | Flow (L/min) | Temperature (degC) |\n|---|---|---|\n| A | 5 | 70 |\n| B | 6 | 10 |\n", encoding="utf-8")
    for number, label in ((1, "A"), (2, "B")):
        for field, column in ((f"mix.m_dot_{number}_kg_s", "Flow"), (f"mix.T_{number}_K", "Temperature")):
            values["variables"][field]["quote"] = {"from": "table", "row": label, "column": column}
    report = run_case(tmp_path, values)
    assert report["audit_pass"] and merge(report)["colour"] == "green"
    assert rows(report)["mix.T_1_K"]["source_entity"] == "row A"


@pytest.mark.parametrize("answer, expected", [(1., True), (0., False)])
def test_given_below_40_question_uses_native_threshold_not_question_text(tmp_path, answer, expected):
    import numpy as np
    from physicsguard.core.registry import VariableRegistry
    from physicsguard.io.source_reading import find_quote, load_sources
    from physicsguard.modules.control import ThresholdStateCheckModule
    from physicsguard.schema.observed_conversion import read_source_value

    values = mixing_values()
    question = (FIXTURES / "question_mix.txt").read_text(encoding="utf-8").replace("37 °C", "40 °C")
    values["claims"][0]["quote"]["text"] = values["claims"][0]["quote"]["text"].replace("37 °C", "40 °C")
    report = run_case(tmp_path, values, question)
    assert report["audit_pass"]
    outlet = rows(report)["mix.T_out_K"]["value"]
    span, _, problem = find_quote({"from": "question", "text": "40 °C"},
                                 load_sources({"question": "question_mix.txt"}, tmp_path))
    assert not problem
    threshold = read_source_value(span, "K")["value"]
    assert threshold == 313.15
    # Finite declared question: 1 means below 40 C, 0 means at/above 40 C.
    check = ThresholdStateCheckModule("answer", {
        "threshold": threshold, "on_value": 0., "off_value": 1., "state_tolerance": .01})
    registry = VariableRegistry()
    for record in check.declare_variables():
        registry.add_variable(record)
    vector = registry.dict_to_vector({"answer.input": outlet, "answer.state": answer})
    residual = check.residuals(np.asarray(vector), registry)[0]
    assert bool(residual.abs_normalized_value <= 1.) is expected
    assert rows(report)["claim:0"]["colour"] == "grey"
    assert rows(report)["claim:0"]["evidence_scope"] == "question_reference"


def test_partial_source_coverage_does_not_claim_all_inputs_were_verified(tmp_path):
    report = _parameter_only_report(
        tmp_path, "SensorLowPassFilterStepModule", {"tau_s": 2., "dt_s": 1.},
        {"true_value_current": 2., "measured_previous": 0., "measured_current": 1.},
        "tau_s", "time constant 2 s", "s")
    row = report.block_verdicts[0]
    assert report.audit_pass and row["colour"] == "green"
    coverage = row["source_coverage"]
    assert coverage["backed_dependencies"] == ["parameter:part.tau_s"]
    assert set(coverage["other_variable_dependencies"]) == {
        "part.true_value_current", "part.measured_previous", "part.measured_current"}
    assert "parameter:part.dt_s" in coverage["unverified_parameters"]
    assert "partial source coverage" in row["source_reason"]
