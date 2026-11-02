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


# Review round 3: a picture above the readable size is folded further, or says plainly what to focus on.

EXAMPLE_AUDITS = sorted(path for path in (ROOT / "examples" / "hierarchical").glob("*/*.yaml")
                        if "hierarchy" in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}))


def _chain_audit(tmp_path, groups, name="chain"):
    """Heaters h0 -> h1 -> ... (T_out = next T_in), one per leaf block; groups maps a parent block to its child count,
    or None to make every leaf block a root."""
    sizes = groups if groups is not None else {None: 30}
    blocks, components, connections, index = [], [], [], 0
    for parent, count in sizes.items():
        if parent is not None:
            blocks.append({"id": parent, "name": f"group {parent}", "level": 0, "components": []})
        for child in range(count):
            block = f"{parent or 'b'}c{child:02d}"
            blocks.append({"id": block, "name": block, "level": 1 if parent else 0, "components": [f"h{index}"],
                           **({"parent_id": parent} if parent else {})})
            components.append({"id": f"h{index}", "type": "CoolantHeatBalanceModule",
                               "parameters": {"cp_J_kgK": 4180.0, "residual_scale_W": 10.0}})
            if index:
                connections.append({"from_variable": f"h{index - 1}.T_out_K", "to_variable": f"h{index}.T_in_K"})
            index += 1
    data = {"audit_name": name, "system": {"system_name": name, "components": components, "connections": connections,
                                           "boundaries": [], "assumptions": []}, "hierarchy": {"blocks": blocks}}
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path, index


def _readable(flow):
    from physicsguard.core.quantity_flow import READABLE_ARROWS, READABLE_BOXES

    return len(flow["nodes"]) <= READABLE_BOXES and len(flow["links"]) <= READABLE_ARROWS


def test_a_block_level_picture_above_the_readable_size_folds_sub_blocks_into_their_parents() -> None:
    """fuel_cell_system drew 15 leaf blocks; its sub-blocks fold into cathode_air_path and coolant_loop."""
    flow = _flow(ROOT / "examples" / "hierarchical" / "fuel_cell_system" / "tree.yaml")
    assert _readable(flow) and flow["too_large"] is None, (len(flow["nodes"]), len(flow["links"]))
    boxes = {row["id"]: row for row in flow["nodes"]}
    assert boxes["block:cathode_air_path"]["folds"] == ["compressor", "exhaust_valve", "humidifier", "intercooler"]
    assert boxes["block:coolant_loop"]["folds"] == ["bypass_or_valve", "coolant_pump", "radiator", "thermal_mass"]
    assert "block:compressor" not in boxes and "block:stack" in boxes
    text = run_cli("hierarchy", "flow", str(ROOT / "examples" / "hierarchical" / "fuel_cell_system" / "tree.yaml")).stdout
    assert '"block cathode_air_path (+4 sub-blocks)"' in text


def test_a_picture_that_cannot_fold_enough_says_what_to_focus_on_and_how_many_boxes_it_holds(tmp_path) -> None:
    path, count = _chain_audit(tmp_path, None)
    flow = _flow(path)
    assert len(flow["nodes"]) == count == 30 and not _readable(flow)
    too_large = flow["too_large"]
    assert (too_large["boxes"], too_large["arrows"]) == (30, 29)
    choices = too_large["focus_choices"]
    assert len(choices) == 30
    for choice in choices[:5]:
        focused = _flow(path, focus=choice["focus"])
        assert (choice["boxes"], choice["arrows"]) == (len(focused["nodes"]), len(focused["links"]))
        assert _readable(focused)
    result = run_cli("hierarchy", "flow", str(path))
    assert result.returncode == 0, result.stderr
    note = next(line for line in result.stdout.splitlines() if line.strip().startswith("n_too_large["))
    assert "too large to read at once: 30 boxes, 29 arrows" in note
    first = choices[0]
    count = lambda number, noun: f"{number} {noun}" + ("" if number == 1 else "es" if noun == "box" else "s")
    assert f"--focus {first['focus']} ({count(first['boxes'], 'box')}, {count(first['arrows'], 'arrow')})" in note
    assert json.loads(run_cli("hierarchy", "flow", str(path), "--json").stdout)["too_large"]["boxes"] == 30


def test_a_folded_box_takes_the_worst_verdict_of_the_blocks_it_draws(tmp_path) -> None:
    from physicsguard.io.observation_loader import load_observed_values

    path, count = _chain_audit(tmp_path, {"p0": 12, "p1": 12})
    variables = {}
    for index in range(count):
        t_in = 300.0 + 10.0 * index
        q = 4180.0 * 2 if index == 12 else 4180.0  # h12, the first heater of p1, is wrong
        variables.update({f"h{index}.m_dot_kg_s": {"value": 0.1, "unit": "kg/s", "external_signal": "flow"},
                          f"h{index}.T_in_K": {"value": t_in, "unit": "K", "external_signal": "inlet"},
                          f"h{index}.T_out_K": {"value": t_in + 10.0, "unit": "K", "external_signal": "outlet"},
                          f"h{index}.Q_dot_W": {"value": q, "unit": "W", "external_signal": "power"}})
    snapshot = tmp_path / "observed.yaml"
    snapshot.write_text(yaml.safe_dump({"observation_name": "chain", "variables": variables}), encoding="utf-8")
    flow = _flow(path, focus="p0", observed=load_observed_values(snapshot))
    boxes = {row["id"]: row for row in flow["nodes"]}
    assert boxes["block:p1"]["verdict"] == "fail" and boxes["block:p1"]["folds"] == ["p1c00"]
    assert flow["too_large"] is not None  # 12 focus boxes and one neighbour: still above the size, and said so


@pytest.mark.parametrize("audit", EXAMPLE_AUDITS, ids=lambda path: path.parent.name + "/" + path.stem)
def test_no_example_draws_a_silent_large_picture(audit) -> None:
    for kwargs in ({}, {"quantity": "mass_flow"}, {"quantity": "power"}):
        flow = _flow(audit, **kwargs)
        assert _readable(flow) or flow["too_large"] is not None, (kwargs, len(flow["nodes"]), len(flow["links"]))


def test_a_one_component_focus_with_too_many_neighbours_says_to_keep_one_quantity(tmp_path) -> None:
    path, count = _chain_audit(tmp_path, None)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # A hub: h0's outlet feeds every other heater, so focusing on h0 draws 30 boxes even at block level.
    data["system"]["connections"] = [{"from_variable": "h0.T_out_K", "to_variable": f"h{index}.T_in_K"}
                                     for index in range(1, count)]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    flow = _flow(path, focus="h0")
    assert flow["too_large"] is not None and flow["too_large"]["focus_choices"] == []
    result = run_cli("hierarchy", "flow", str(path), "--focus", "h0")
    note = next(line for line in result.stdout.splitlines() if line.strip().startswith("n_too_large["))
    assert "its one component has many neighbours: keep one quantity with --quantity" in note
