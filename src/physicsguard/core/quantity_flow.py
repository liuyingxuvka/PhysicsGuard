"""How physical quantities flow through an audit, computed from the audit's own relations.

A link A -> B means a quantity owned by component A reaches component B: either a
declared connection (A.x = B.y) or a relation of B that reads A's variable. The reads
come from tracing each native relation once at the registry's declared initial
guesses; nothing is solved and no observed value is used unless a snapshot is given
to colour the verdicts. The picture shows the part under discussion and names what it
leaves out. Above the readable size it folds sub-blocks into their parent blocks, one
level at a time, but never into a single box while a finer level has more; when no
level fits, it draws the smallest level that still has more than one box, says so in
the picture and names the blocks to focus on, with the size of each focused picture.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from html import escape
from typing import Any

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.units import QUANTITY_EXPONENTS, unit_quantity

# About as many boxes and arrows as a person reads at once; beyond it the tool draws blocks, not components,
# and folds sub-blocks into their parents until the picture fits.
READABLE_BOXES = 12
READABLE_ARROWS = 20
LABELS_PER_ARROW = 3
# Focus choices named in the picture's note when it is still too large; --json lists them all.
FOCUS_CHOICES_SHOWN = 8


@dataclass
class _Link:
    source: str
    target: str
    labels: list[str] = field(default_factory=list)


@dataclass
class _Drawing:
    level: str
    nodes: list[str]
    links: dict[tuple[str, str], _Link]
    hidden_links: int
    members: dict[str, list[str]]

    def fits(self) -> bool:
        return len(self.nodes) <= READABLE_BOXES and len(self.links) <= READABLE_ARROWS


def quantity_flow(spec: Any, *, focus: str | None = None, quantity: str | None = None,
                  observed: Any | None = None) -> dict[str, Any]:
    """The nodes, links and omissions of the quantity-flow picture; raises ValueError on an unknown focus or quantity."""
    from physicsguard.core.hierarchy import BlockIndex

    index = BlockIndex(spec.hierarchy, spec.system)
    components = [component.id for component in spec.system.components]
    block_of = {name: index.component_block(name) or "(unassigned)" for name in components}
    # Each component's blocks from the top of the tree down to its own block.
    chains = {name: ([block.id for block in reversed(index.ancestors(block_of[name]))] + [block_of[name]]
                     if block_of[name] in index.block_ids() else [block_of[name]]) for name in components}
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
    if focus_components is not None:
        shown = _neighbourhood(links, focus_components)
    elif quantity is not None:
        # Only the components a link of this quantity touches; the rest are listed as not shown.
        shown = {name for link in links.values() for name in (link.source, link.target)}
    else:
        shown = set(components)
    drawing = _fold(links, shown, focus_components or set(), chains)
    too_large = None
    if not drawing.fits():
        too_large = {"boxes": len(drawing.nodes), "arrows": len(drawing.links), "readable_boxes": READABLE_BOXES,
                     "readable_arrows": READABLE_ARROWS,
                     "focus_choices": _focus_choices(links, shown, focus_components, chains, components, block_of, index)}
    omitted_components = sorted(set(components) - shown)
    failing = sorted(block for block, verdict in verdicts.items() if verdict == "fail")
    return {
        "audit_name": spec.audit_name,
        "level": drawing.level,
        "focus": sorted(focus_components) if focus_components is not None else None,
        "focus_reason": "named" if focus is not None else ("failing blocks " + ", ".join(failing)) if failing and focus_components else None,
        "quantity": quantity,
        "nodes": [_node_row(name, spec, block_of, verdicts, drawing, chains) for name in drawing.nodes],
        "links": [{"from": link.source, "to": link.target, "quantities": link.labels} for link in drawing.links.values()],
        "omitted": {
            "components": omitted_components,
            "blocks": sorted({block_of[name] for name in omitted_components}),
            "links": drawing.hidden_links,
            "links_of_other_quantities": filtered,
            "boundary_and_assumption_values": external,
            "untraced_relations": untraced,
        },
        "too_large": too_large,
        "basis": ("arrow A -> B: a relation of B uses a quantity of A, or a connection A.x = B.y; "
                  "relations traced once at the declared initial guesses; no solve"),
    }


def _neighbourhood(links: dict[tuple[str, str], _Link], focus_components: set[str]) -> set[str]:
    """The focus components and every component one link away from them."""
    shown = set(focus_components)
    for link in links.values():
        if link.source in focus_components:
            shown.add(link.target)
        if link.target in focus_components:
            shown.add(link.source)
    return shown


def _draw(links: dict[tuple[str, str], _Link], shown: set[str], box: Any, level: str) -> _Drawing:
    """Boxes and merged arrows when each shown component is drawn as box(component)."""
    drawn: dict[tuple[str, str], _Link] = {}
    hidden = 0
    for link in links.values():
        if link.source not in shown or link.target not in shown:
            hidden += 1
            continue
        source, target = box(link.source), box(link.target)
        if source == target:
            continue
        merged = drawn.setdefault((source, target), _Link(source, target))
        merged.labels.extend(label for label in link.labels if label not in merged.labels)
    members: dict[str, list[str]] = defaultdict(list)
    for name in sorted(shown):
        members[box(name)].append(name)
    nodes = sorted(members, key=lambda item: (item.startswith("block:"), item))
    return _Drawing(level, nodes, drawn, hidden, dict(members))


def _fold(links: dict[tuple[str, str], _Link], shown: set[str], keep: set[str],
          chains: dict[str, list[str]]) -> _Drawing:
    """The finest drawing within the readable size: components, then blocks, folding sub-blocks into their parents
    one level at a time. The components in keep (a focus) stay expanded. A drawing of one box hides all structure, so
    it is never chosen while a finer one has more boxes; when no drawing with more than one box fits, the coarsest of
    them is returned (a single root's children, not the root alone) and the caller says what to focus on."""
    finest = _draw(links, shown, lambda name: name, "component")
    drawings = [finest]
    if not finest.fits():
        for depth in range(max(len(chains[name]) for name in shown) - 1, -1, -1):
            def box(name: str, depth: int = depth) -> str:
                return name if name in keep else "block:" + chains[name][min(depth, len(chains[name]) - 1)]

            drawings.append(_draw(links, shown, box, "focus" if keep else "block"))
    useful = [drawing for drawing in drawings if len(drawing.nodes) > 1] or drawings[:1]
    return next((drawing for drawing in useful if drawing.fits()), useful[-1])


def _focus_choices(links, shown, focus_components, chains, components, block_of, index) -> list[dict[str, Any]]:
    """Each block that draws a narrower part of this picture, with the boxes and arrows its focused picture holds;
    readable ones first, larger parts first."""
    current = focus_components or set()
    choices = []
    for block in index.block_ids():
        inside = {block} | {child.id for child in index.descendants(block)}
        part = {name for name in components if block_of[name] in inside}
        narrower = part < current if focus_components is not None else bool(part & shown) and not shown <= part
        if not part or not narrower:
            continue
        drawing = _fold(links, _neighbourhood(links, part), part, chains)
        choices.append({"focus": block, "components": len(part), "boxes": len(drawing.nodes),
                        "arrows": len(drawing.links), "readable": drawing.fits()})
    return sorted(choices, key=lambda row: (not row["readable"], -row["components"], row["focus"]))


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


def _node_row(name: str, spec: Any, block_of: dict[str, str], verdicts: dict[str, str], drawing: _Drawing,
              chains: dict[str, list[str]]) -> dict[str, Any]:
    if name.startswith("block:"):
        block = name.removeprefix("block:")
        names = {item.id: item.name for item in spec.hierarchy.blocks}
        members = drawing.members[name]
        # Sub-blocks folded into this box, and the worst verdict of the blocks whose components it draws.
        folds = sorted({sub for member in members for sub in chains[member][chains[member].index(block) + 1:]})
        drawn = [verdicts.get(chains[member][-1]) for member in members]
        verdict = "fail" if "fail" in drawn else "pass" if "pass" in drawn else None
        return {"id": name, "kind": "block", "block": block, "name": names.get(block), "folds": folds, "verdict": verdict}
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
                if row["folds"]:
                    text += f" (+{_count(len(row['folds']), 'sub-block')})"
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
    folded = ", sub-blocks folded into their parents" if any(row.get("folds") for row in flow["nodes"]) else ""
    lines.append(f"  %% shown: {len(flow['nodes'])} boxes ({flow['level']} level{folded}), {len(flow['links'])} arrows")
    notes = []
    if omitted:
        lines.append(f'  n_omitted["not shown: {label(omitted)}"]')
        notes.append("n_omitted")
    if flow["too_large"]:
        lines.append(f'  n_too_large["{label(_too_large_sentence(flow["too_large"], flow["focus"]))}"]')
        notes.append("n_too_large")
    if notes:
        lines.append("  classDef omitted stroke-dasharray: 4 3,fill:none")
        lines.append(f"  class {','.join(notes)} omitted")
    for verdict, style in (("fail", "fill:#f8d7da,stroke:#b02a37"), ("pass", "fill:#d1e7dd,stroke:#146c43")):
        marked = [ids[row["id"]] for row in flow["nodes"] if row["verdict"] == verdict]
        if marked:
            lines.append(f"  classDef {verdict} {style}")
            lines.append(f"  class {','.join(marked)} {verdict}")
    return "\n".join(lines)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "es" if noun.endswith("x") else "s")


def _too_large_sentence(too_large: dict[str, Any], focus: list[str] | None) -> str:
    """Plain words: the picture's size, the readable size, and what to focus on with each focused picture's size."""
    sentence = (f"too large to read at once: {_count(too_large['boxes'], 'box')}, {_count(too_large['arrows'], 'arrow')} "
                f"(about {too_large['readable_boxes']} boxes and {too_large['readable_arrows']} arrows read well); ")
    choices = too_large["focus_choices"]
    if not choices and len(focus or []) == 1:
        return sentence + "its one component has many neighbours: keep one quantity with --quantity"
    if not choices:
        return sentence + ("no block inside it is smaller: focus on one component with --focus COMPONENT, "
                           "or keep one quantity with --quantity")
    named = [f"--focus {row['focus']} ({_count(row['boxes'], 'box')}, {_count(row['arrows'], 'arrow')})"
             for row in choices[:FOCUS_CHOICES_SHOWN]]
    more = len(choices) - len(named)
    return (sentence + "draw one part instead: " + ", ".join(named) + (f", and {more} more (--json lists them)" if more else "")
            + ", or keep one quantity with --quantity")


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
