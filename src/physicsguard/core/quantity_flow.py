"""How physical quantities flow through an audit, computed from the audit's own relations.

A link A -> B means a quantity owned by component A reaches component B: either a
declared connection (A.x = B.y) or a relation of B that reads A's variable. The reads
come from tracing each native relation once at the registry's declared initial
guesses; nothing is solved and no observed value is used unless a snapshot is given
to colour the verdicts. The picture shows the part under discussion and names what it
leaves out.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from html import escape
from typing import Any

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.units import QUANTITY_EXPONENTS, unit_quantity

# About as many boxes as a person reads at once; beyond it the tool draws blocks, not components.
READABLE_BOXES = 12
LABELS_PER_ARROW = 3


@dataclass
class _Link:
    source: str
    target: str
    labels: list[str] = field(default_factory=list)


def quantity_flow(spec: Any, *, focus: str | None = None, quantity: str | None = None,
                  observed: Any | None = None) -> dict[str, Any]:
    """The nodes, links and omissions of the quantity-flow picture; raises ValueError on an unknown focus or quantity."""
    from physicsguard.core.hierarchy import BlockIndex

    index = BlockIndex(spec.hierarchy, spec.system)
    components = [component.id for component in spec.system.components]
    block_of = {name: index.component_block(name) or "(unassigned)" for name in components}
    if quantity is not None and quantity not in QUANTITY_EXPONENTS and unit_quantity(quantity) is None:
        raise ValueError(f"unknown quantity {quantity!r}: use one of {', '.join(sorted(QUANTITY_EXPONENTS))} or a unit from the unit table")

    builder = ResidualBuilder(spec.system)
    registry = builder.build_registry()
    dependencies: list[Any] = []
    records = builder.diagnostic_residual_records(registry.initial_vector(), _dependencies=dependencies)
    links: dict[tuple[str, str], _Link] = {}
    untraced: list[str] = []
    external = 0
    filtered = 0

    def unit(variable: str) -> str:
        return str(registry.get_record(variable).unit or "")

    def add(source_variable: str, target_component: str, label: str) -> None:
        nonlocal filtered
        source = source_variable.split(".", 1)[0]
        if source == target_component:
            return
        if quantity is not None and quantity not in (unit(source_variable), unit_quantity(unit(source_variable))):
            filtered += 1
            return
        link = links.setdefault((source, target_component), _Link(source, target_component))
        text = f"{label} [{unit(source_variable) or '-'}]"
        if text not in link.labels:
            link.labels.append(text)

    for record, reads in zip(records, dependencies):
        if record.source == "connection":
            left, right = record.name.removeprefix("connection:").split("=", 1)
            add(left, right.split(".", 1)[0], f"{left.split('.', 1)[1]} = {right.split('.', 1)[1]}")
        elif record.source in {"boundary", "assumption"}:
            external += 1
        elif reads is None:
            untraced.append(record.name)
        else:
            for variable in sorted(reads):
                add(variable, record.source, variable.split(".", 1)[1])

    verdicts = _block_verdicts(spec, observed) if observed is not None else {}
    focus_components = _focus_components(focus, verdicts, components, block_of, index)
    neighbours: set[str] = set()
    if focus_components is not None:
        for link in links.values():
            if link.source in focus_components:
                neighbours.add(link.target)
            if link.target in focus_components:
                neighbours.add(link.source)
        neighbours -= focus_components
        shown = focus_components | neighbours
    elif quantity is not None:
        # Only the components a link of this quantity touches; the rest are listed as not shown.
        shown = {name for link in links.values() for name in (link.source, link.target)}
    else:
        shown = set(components)
    level = "component" if len(shown) <= READABLE_BOXES else "block"
    if focus_components is not None and level == "block":
        # The focus stays expanded; its neighbours fold into their blocks.
        level = "focus"

    def node(component: str) -> str:
        if level == "component" or (level == "focus" and component in focus_components):
            return component
        return "block:" + block_of[component]

    drawn: dict[tuple[str, str], _Link] = {}
    hidden_links = 0
    for link in links.values():
        if link.source not in shown or link.target not in shown:
            hidden_links += 1
            continue
        source, target = node(link.source), node(link.target)
        if source == target:
            continue
        merged = drawn.setdefault((source, target), _Link(source, target))
        merged.labels.extend(label for label in link.labels if label not in merged.labels)
    nodes = sorted({node(name) for name in shown}, key=lambda item: (item.startswith("block:"), item))
    omitted_components = sorted(set(components) - shown)
    failing = sorted(block for block, verdict in verdicts.items() if verdict == "fail")
    return {
        "audit_name": spec.audit_name,
        "level": level,
        "focus": sorted(focus_components) if focus_components is not None else None,
        "focus_reason": "named" if focus is not None else ("failing blocks " + ", ".join(failing)) if failing and focus_components else None,
        "quantity": quantity,
        "nodes": [_node_row(name, spec, block_of, verdicts) for name in nodes],
        "links": [{"from": link.source, "to": link.target, "quantities": link.labels} for link in drawn.values()],
        "omitted": {
            "components": omitted_components,
            "blocks": sorted({block_of[name] for name in omitted_components}),
            "links": hidden_links,
            "links_of_other_quantities": filtered,
            "boundary_and_assumption_values": external,
            "untraced_relations": untraced,
        },
        "basis": ("arrow A -> B: a relation of B uses a quantity of A, or a connection A.x = B.y; "
                  "relations traced once at the declared initial guesses; no solve"),
    }


def _block_verdicts(spec: Any, observed: Any) -> dict[str, str]:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner

    report = HierarchicalAuditRunner(spec).evaluate_observed(
        observed, top_n_blocks=len(spec.hierarchy.blocks), _unit_factor_hints=False, _resolution=False)
    verdicts = {}
    for block in report.top_blocks:
        if block.checked_residuals:
            verdicts[block.block_id] = "pass" if block.own_audit_pass else "fail"
    return verdicts


def _focus_components(focus, verdicts, components, block_of, index) -> set[str] | None:
    if focus is not None:
        if focus in components:
            return {focus}
        if focus in index.block_ids():
            blocks = {focus} | {block.id for block in index.descendants(focus)}
            return {name for name in components if block_of[name] in blocks}
        raise ValueError(f"unknown focus {focus!r}: name a block ({', '.join(index.block_ids())}) or a component")
    failing = {block for block, verdict in verdicts.items() if verdict == "fail"}
    if failing:
        return {name for name in components if block_of[name] in failing}
    return None


def _node_row(name: str, spec: Any, block_of: dict[str, str], verdicts: dict[str, str]) -> dict[str, Any]:
    if name.startswith("block:"):
        block = name.removeprefix("block:")
        names = {item.id: item.name for item in spec.hierarchy.blocks}
        return {"id": name, "kind": "block", "block": block, "name": names.get(block), "verdict": verdicts.get(block)}
    types = {component.id: component.type for component in spec.system.components}
    return {"id": name, "kind": "component", "type": types[name], "block": block_of[name],
            "verdict": verdicts.get(block_of[name])}


def render_quantity_flow_mermaid(flow: dict[str, Any]) -> str:
    """Mermaid text: generated node ids, escaped labels, one arrow per pair, and a visible note of what is left out."""
    label = lambda value: escape(" ".join(str(value).splitlines()), quote=True)
    ids = {row["id"]: f"n{i}" for i, row in enumerate(flow["nodes"])}
    what = f"quantity flow of {flow['audit_name']}"
    if flow["quantity"]:
        what += f", {flow['quantity']} only"
    if flow["focus"]:
        what += ", around " + ", ".join(flow["focus"])
        if flow["focus_reason"] != "named":
            what += f" ({flow['focus_reason']})"
    lines = ["flowchart LR", f"  %% {what}; {flow['basis']}"]
    by_block: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in flow["nodes"]:
        by_block[row["block"]].append(row)
    for number, (block, rows) in enumerate(by_block.items()):
        components = [row for row in rows if row["kind"] == "component"]
        for row in rows:
            if row["kind"] == "block":
                text = f"block {block}" + (f": {row['name']}" if row.get("name") else "")
                lines.append(f'  {ids[row["id"]]}["{label(text)}"]')
        if components:
            lines.append(f'  subgraph b{number}["{label(block)}"]')
            for row in components:
                lines.append(f'    {ids[row["id"]]}["{label(row["id"])}: {label(row["type"])}"]')
            lines.append("  end")
    for link in flow["links"]:
        names = link["quantities"][:LABELS_PER_ARROW]
        extra = len(link["quantities"]) - len(names)
        text = "; ".join(names) + (f"; +{extra} more" if extra else "")
        lines.append(f'  {ids[link["from"]]} -->|"{label(text)}"| {ids[link["to"]]}')
    omitted = _omitted_sentence(flow["omitted"])
    lines.append(f"  %% shown: {len(flow['nodes'])} boxes ({flow['level']} level), {len(flow['links'])} arrows")
    if omitted:
        lines.append(f'  n_omitted["not shown: {label(omitted)}"]')
        lines.append("  classDef omitted stroke-dasharray: 4 3,fill:none")
        lines.append("  class n_omitted omitted")
    for verdict, style in (("fail", "fill:#f8d7da,stroke:#b02a37"), ("pass", "fill:#d1e7dd,stroke:#146c43")):
        marked = [ids[row["id"]] for row in flow["nodes"] if row["verdict"] == verdict]
        if marked:
            lines.append(f"  classDef {verdict} {style}")
            lines.append(f"  class {','.join(marked)} {verdict}")
    return "\n".join(lines)


def _omitted_sentence(omitted: dict[str, Any]) -> str:
    parts = []
    if omitted["components"]:
        parts.append(f"{len(omitted['components'])} components (blocks {', '.join(omitted['blocks'])})")
    if omitted["links"]:
        parts.append(f"{omitted['links']} links to them")
    if omitted["links_of_other_quantities"]:
        parts.append(f"{omitted['links_of_other_quantities']} links of other quantities")
    if omitted["boundary_and_assumption_values"]:
        parts.append(f"{omitted['boundary_and_assumption_values']} boundary/assumption values")
    if omitted["untraced_relations"]:
        parts.append(f"{len(omitted['untraced_relations'])} relations whose inputs could not be traced")
    return "; ".join(parts)


__all__ = ["quantity_flow", "render_quantity_flow_mermaid"]
