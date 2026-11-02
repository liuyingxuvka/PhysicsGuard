"""The quantity-flow picture is computed from the audit's relations and says what it leaves out."""
from __future__ import annotations

import json

import pytest
import yaml

from conftest import ROOT, TANK, run_cli

SHOWER = ROOT / "examples" / "hierarchical" / "shower_mix"


def _flow(path, **kwargs):
    from physicsguard.core.quantity_flow import quantity_flow
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    return quantity_flow(load_hierarchical_audit_spec(path), **kwargs)


def test_small_audit_draws_every_component_and_merges_parallel_links() -> None:
    flow = _flow(SHOWER / "audit.yaml")
    assert flow["level"] == "component"
    assert [row["id"] for row in flow["nodes"]] == ["heater", "mix"]
    assert flow["links"] == [{"from": "heater", "to": "mix", "quantities": [
        "m_dot_kg_s = m_dot_1_kg_s [kg/s]", "T_out_K = T_1_K [K]", "T_in_K = T_2_K [K]"]}]
    assert flow["omitted"]["components"] == [] and flow["omitted"]["links"] == 0


def test_links_come_from_the_relations_not_only_from_declared_connections() -> None:
    flow = _flow(TANK / "heated_tank.yaml", focus="qout")
    # qout's sum relation reads three quantities of other components; none of them is a declared connection.
    into = [link for link in flow["links"] if link["to"] == "qout"]
    assert {link["from"] for link in into} == {"heat", "loss", "through"}
    assert all("=" not in label for link in into for label in link["quantities"])


def test_the_picture_follows_the_model(tmp_path) -> None:
    data = yaml.safe_load((SHOWER / "audit.yaml").read_text(encoding="utf-8"))
    data["system"]["connections"] = [row for row in data["system"]["connections"] if row["to_variable"] != "mix.T_2_K"]
    path = tmp_path / "audit.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    labels = _flow(path)["links"][0]["quantities"]
    assert "T_in_K = T_2_K [K]" not in labels and len(labels) == 2


def test_a_large_audit_is_drawn_by_block_and_a_focus_expands_only_its_neighbourhood() -> None:
    whole = _flow(TANK / "heated_tank.yaml")
    assert whole["level"] == "block" and len(whole["nodes"]) == 6
    focused = _flow(TANK / "heated_tank.yaml", focus="throughflow")
    assert focused["level"] == "component"
    assert {row["id"] for row in focused["nodes"]} == {"through", "inflow_mass", "heat", "qout"}
    assert len(focused["omitted"]["components"]) == 10
    assert focused["omitted"]["links"] > 0


def test_a_quantity_filter_keeps_only_that_quantity_and_counts_the_rest() -> None:
    flow = _flow(TANK / "heated_tank.yaml", quantity="power")
    labels = [label for link in flow["links"] for label in link["quantities"]]
    assert labels and all(label.endswith("[W]") for label in labels)
    assert flow["omitted"]["links_of_other_quantities"] > 0
    assert "lvl_prev" in flow["omitted"]["components"]


def test_an_observed_snapshot_focuses_on_the_failing_block_and_colours_it() -> None:
    from physicsguard.io.observation_loader import load_observed_values

    flow = _flow(SHOWER / "audit.yaml", observed=load_observed_values(SHOWER / "observed_ai.yaml"))
    assert flow["focus"] == ["mix"] and flow["focus_reason"] == "failing blocks mixer"
    verdicts = {row["id"]: row["verdict"] for row in flow["nodes"]}
    assert verdicts == {"heater": "pass", "mix": "fail"}


def test_unknown_focus_or_quantity_is_refused_by_name() -> None:
    with pytest.raises(ValueError, match="unknown focus 'nowhere'"):
        _flow(SHOWER / "audit.yaml", focus="nowhere")
    with pytest.raises(ValueError, match="unknown quantity 'colour'"):
        _flow(SHOWER / "audit.yaml", quantity="colour")


def test_command_prints_mermaid_with_a_visible_note_of_what_is_left_out() -> None:
    result = run_cli("hierarchy", "flow", str(TANK / "heated_tank.yaml"), "--focus", "throughflow")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "flowchart LR"
    note = next(line for line in lines if line.strip().startswith("n_omitted["))
    assert "not shown: 10 components (blocks envelope, heater, hydraulics, tank)" in note
    assert any("-->|" in line for line in lines)
    data = json.loads(run_cli("hierarchy", "flow", str(TANK / "heated_tank.yaml"), "--json").stdout)
    assert data["level"] == "block"
    refused = run_cli("hierarchy", "flow", str(SHOWER / "audit.yaml"), "--focus", "nowhere")
    assert refused.returncode == 2 and "unknown focus 'nowhere'" in refused.stderr


def test_readme_discussion_example_is_the_command_output() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index("```mermaid\n", text.index("## Discuss it with a picture")) + len("```mermaid\n")
    shown = text[start:text.index("```", start)].rstrip("\n")
    result = run_cli("hierarchy", "flow", "examples/hierarchical/heated_tank/heated_tank.yaml",
                     "--observed", "examples/hierarchical/heated_tank/measured_k70.yaml")
    assert result.returncode == 0, result.stderr
    assert shown == result.stdout.rstrip("\n")
