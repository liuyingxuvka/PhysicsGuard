"""One tree view for an audit: the declared structure, and on it the verdicts of a run.

The view only reads dictionaries: the structure from ``describe_hierarchy`` and,
when given, a hierarchy report (``to_dict`` of ``run``, ``evaluate_observed`` or
``compare_observed``) or a fault-variant result. Verdicts are never recomputed:
each block's verdict comes from the report's ``block_verdicts`` rows.
"""

from __future__ import annotations

from typing import Any

__all__ = ["render_tree_view"]

LIST_LIMIT = 5


def _short(items: list[Any], limit: int = LIST_LIMIT) -> str:
    items = [str(item) for item in items]
    text = ", ".join(items[:limit])
    return text + (f" +{len(items) - limit} more" if len(items) > limit else "")


def _flag(value: Any) -> str:
    return "PASS" if value else "FAIL"


def _card_blocks(description: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    """Place each assumption card on the block that owns the component of its target."""
    owner = {component: block["id"] for block in description["blocks"] for component in block["component_ids"]}
    placed: dict[str, list[str]] = {}
    unplaced: list[str] = []
    for card in description.get("assumptions", []):
        block = owner.get(str(card.get("target") or "").split(".", 1)[0])
        if block is None:
            unplaced.append(card["id"])
        else:
            placed.setdefault(block, []).append(card["id"])
    return placed, unplaced


def _structure_parts(block: dict[str, Any], depth: int, cards: list[str], *, full: bool = True) -> list[str]:
    if not full:
        return [f"{'  ' * depth}{block['id']} [L{block['level']}]"] + (["assumptions: " + ", ".join(cards)] if cards else [])
    parts = [f"{'  ' * depth}{block['id']} [L{block['level']}] components: "
             + (", ".join(f"{c['id']}({c['type']})" for c in block["components"]) or "none")]
    if block["refines"]:
        parts.append("refines: " + ", ".join(block["refines"]))
    if block["fault_variants"]:
        parts.append("variants: " + ", ".join(block["fault_variants"]))
    if block["refinement_rules"]:
        parts.append("rules: " + "; ".join(
            f"{rule['id']} -> " + ", ".join(f"{target} ({rule['template_status'][target]})" for target in rule["next_template_ids"])
            for rule in block["refinement_rules"]))
    if block["required_variables"]:
        parts.append("needs: " + ", ".join(block["required_variables"]))
    if cards:
        parts.append("assumptions: " + ", ".join(cards))
    if "signals" in block:
        signals = block["signals"]
        parts.append(f"signals: {signals['mapped']} mapped, {signals['review_required']} review_required, "
                     f"{signals['declared_required_missing']} declared needs missing")
    return parts


def _verdict_part(row: dict[str, Any]) -> str:
    """own PASS|FAIL only for a block with checked residuals; never PASS without one."""
    parts = []
    if row["checked_residual_count"]:
        text = f"own {_flag(row['own_audit_pass'])} {row['max_abs_normalized_residual']:.2f} ({row['checked_residual_count']} checked)"
        top = row.get("top_residual")
        if not row["own_audit_pass"] and top:
            text += f": {top['name']} {top['normalized_value']:.2f}"
        parts.append(text)
    if row["missing_required_variables"]:
        parts.append(f"not checked: {len(row['missing_required_variables'])} inputs missing")
    return " | ".join(parts) if parts else "no checks"


def _variant_part(block_id: str, variants: dict[str, Any]) -> str | None:
    failing = [f"{row['id']}({row['signature'][block_id]})" for row in variants["variants"]
               if block_id in (row.get("signature") or {})]
    return "variants failing here: " + _short(failing) if failing else None


def _report_head(description: dict[str, Any], report: dict[str, Any], comparison: dict[str, Any] | None) -> str:
    metadata = report.get("metadata", {})
    ledger = report.get("signal_mapping_ledger", [])
    observation = (comparison or {}).get("observation_name") or metadata.get("observation_name")
    if comparison is None and metadata.get("solver_attempted"):
        where = "(reference solve)"
    else:
        where = f"on {observation or 'observed values'}"
    head = (f"audit {description['audit_name']} {where}: {_flag(report['audit_pass'])}; "
            f"{len(report.get('checked_residuals', []))} checked, {len(report.get('unchecked_residuals', {}))} unchecked, "
            f"{len(report.get('derived_variables', {}))} derived; "
            f"mapping {len(ledger)} rows, {sum(bool(row.get('issue_codes')) for row in ledger)} with issues")
    if comparison is not None:
        head += f"; reference {_flag(comparison['reference_audit_pass'])}"
    return head


def _report_tail(report: dict[str, Any], comparison: dict[str, Any] | None) -> list[str]:
    lines = []
    for check in report.get("refinement_checks", []):
        consistent = {True: "yes", False: "no", None: "not checked"}[check.get("consistent")]
        coarse = "not checked" if check.get("coarse_pass") is None else _flag(check["coarse_pass"])
        lines.append(f"refinement: {check['parent']} coarse {coarse}, children {_flag(check['children_pass'])}, consistent {consistent}")
    for rec in report.get("recommended_refinements", []):
        targets = ", ".join(f"{name} ({rec['template_status'].get(name, 'planned')})" for name in rec["next_template_ids"]) or "no template"
        needs = _short(rec["next_required_variables"]) or "nothing declared"
        lines.append(f"next: {rec['rule_id']} -> {targets} needs {needs}")
    issues = [f"{row['physics_variable']} {','.join(row['issue_codes'])}" for row in report.get("signal_mapping_ledger", [])
              if row.get("issue_codes")]
    if issues:
        lines.append("mapping: " + _short(issues))
    if report.get("warnings"):
        lines.append("warnings: " + "; ".join(
            item if len(item) <= 160 else item[:157] + "..." for item in report["warnings"][:LIST_LIMIT])
            + (f" +{len(report['warnings']) - LIST_LIMIT} more" if len(report["warnings"]) > LIST_LIMIT else ""))
    solved = comparison is not None or report.get("metadata", {}).get("solver_attempted")
    if solved:
        success = comparison["reference_optimization_success"] if comparison is not None else report.get("optimization_success")
        lines.append(f"optimization_success: {'true' if success else 'false'}")
    return lines


def _variants_tail(variants: dict[str, Any]) -> list[str]:
    lines = [f"ok: {'yes' if variants['ok'] else 'no'}", f"nominal: {_flag(variants['nominal_audit_pass'])}"]
    for row in variants["variants"]:
        if row["kind"] == "benign":
            state = "neutral" if row.get("neutral") else "not neutral"
        else:
            state = "detected" if row.get("detected") else "not detected"
        met = "met" if row.get("expect_blocks_met") else "not met"
        lines.append(f"variant {row['id']} {row['kind']}: {state}, fails {_short(row.get('failed_blocks') or []) or 'none'}, "
                     f"expected {_short(row.get('expected_blocks') or []) or 'none'} {met}")
    for row in variants.get("pairs", []):
        lines.append(f"pair {row['id']}: {row.get('pair_status')}")
    if variants.get("masked_pairs"):
        lines.append("masked: " + _short(variants["masked_pairs"]))
    for group in variants.get("indistinguishable", [])[:LIST_LIMIT]:
        lines.append(f"indistinguishable: {'+'.join(group['variant_ids'])} next signal {group.get('next_signal') or 'none'}")
    if variants.get("model_miss") is not None:
        lines.append("matches: " + (_short(variants.get("matching_variants") or []) or "none"))
        lines.append(f"model miss: {'yes' if variants['model_miss'] else 'no'}")
    lines.append(f"boundary: {variants['claim_boundary']}")
    return lines


def render_tree_view(description: dict[str, Any], report: dict[str, Any] | None = None,
                     variants: dict[str, Any] | None = None, *, full: bool = False) -> str:
    """Render the declared tree; with a report or a variant result, add each block's verdict."""
    comparison = report if report is not None and "observed_hierarchy" in report else None
    audit = comparison["observed_hierarchy"] if comparison is not None else report
    blocks = {block["id"]: block for block in description["blocks"]}
    verdicts = {row["block_id"]: row for row in (audit or {}).get("block_verdicts", [])}
    if audit is not None and set(verdicts) != set(blocks):
        raise ValueError("report block_verdicts do not cover the tree's blocks")
    cards, unplaced = _card_blocks(description)
    show_structure = full or (audit is None and variants is None)
    if audit is not None:
        lines = [_report_head(description, audit, comparison)]
    elif variants is not None:
        lines = [f"audit {description['audit_name']} variants: {len(variants['variants'])} variants, "
                 f"{len(variants.get('pairs', []))} pairs"]
    else:
        listed = description["fault_variants"]
        benign = [variant["id"] for variant in listed if variant["kind"] == "benign"]
        lines = [f"audit {description['audit_name']}: {len(blocks)} blocks, {description['component_count']} components, "
                 f"{len(listed)} variants ({len(benign)} benign), "
                 f"{len(description['refinement_rules'])} refinement rules, {len(description['assumptions'])} assumptions"
                 + (f"; benign: {', '.join(benign)}" if benign else "")]

    def visit(identifier: str, depth: int) -> None:
        block = blocks[identifier]
        parts = _structure_parts(block, depth, cards.get(identifier, []), full=show_structure)
        if audit is not None:
            parts.append(_verdict_part(verdicts[identifier]))
        if variants is not None:
            extra = _variant_part(identifier, variants)
            if extra:
                parts.append(extra)
        lines.append(" | ".join(parts))
        for child in block["children"]:
            visit(child, depth + 1)

    for root in description["root_blocks"]:
        visit(root, 0)
    links: dict[tuple[str, str], int] = {}
    for connection in description["connections"]:
        if connection["scope"] == "between_blocks":
            pair = (connection["from_block"] or "unassigned", connection["to_block"] or "unassigned")
            links[pair] = links.get(pair, 0) + 1
    if links and show_structure:
        lines.append("links: " + ", ".join(f"{source} -> {target} ({count})" for (source, target), count in links.items()))
    if description["unassigned_components"]:
        lines.append("unassigned: " + ", ".join(description["unassigned_components"]))
    if unplaced:
        lines.append("assumptions (no block): " + ", ".join(unplaced))
    if audit is not None:
        lines.extend(_report_tail(audit, comparison))
    if variants is not None:
        lines.extend(_variants_tail(variants))
    return "\n".join(lines)
