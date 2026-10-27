"""Model-derived alternate-device fault signatures and discrimination."""

from __future__ import annotations

from itertools import combinations
import math
from pathlib import Path
from typing import Any

from physicsguard.core._residual_dependencies import residual_trace_scope
from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.core.residual import ResidualBuilder
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec


class _VariantNotEvaluable(ValueError):
    """A valid edit leaves its requested generated measurement unavailable."""


def _signature(report) -> dict[str, str]:
    """Use own checked failures, including internal blocks with genuine failures."""
    result = {}
    for block in report.top_blocks:
        if block.own_audit_pass or not block.top_residuals:
            continue
        value = max(block.top_residuals, key=lambda item: item.abs_normalized_value).normalized_value
        result[block.block_id] = "+" if value > 0 else "-" if value < 0 else "0"
    return dict(sorted(result.items()))


def _variant_device(spec, variants):
    device = spec.model_copy(deep=True)
    components = {component.id: component for component in device.system.components}
    for variant in variants:
        for target, value in variant.parameters.items():
            component_id, parameter = target.rsplit(".", 1)
            if component_id not in components:
                raise ValueError(f"variant parameter references unknown component: {target}")
            # Preserve the existing constructor's parameter contract, including
            # legal defaults absent from YAML; do not invent a second registry.
            components[component_id].parameters[parameter] = value
    return device


def _variant_audit(spec, data, base_dir):
    try:
        return HierarchicalAuditRunner(spec, base_dir).evaluate_observed(
            data, skip_unobserved=True, top_n_blocks=len(spec.hierarchy.blocks), _unit_factor_hints=False)
    except ValueError as exc:
        if "no residual can be evaluated without them" in str(exc):
            raise _VariantNotEvaluable(str(exc)) from exc
        raise


def _variant_data(spec, nominal, variants, base_dir):
    device = _variant_device(spec, variants)
    data = nominal.model_copy(deep=True)
    registry = ResidualBuilder(device.system).build_registry()
    names = set(registry.names())
    blocks = {block.id for block in spec.hierarchy.blocks}
    rederive = set()
    ids = [variant.id for variant in variants]
    for variant in variants:
        if set(variant.expect_blocks) - blocks:
            raise ValueError(f"variant {variant.id}: unknown expect_blocks")
        for change in variant.changes:
            if change.variable not in names or change.variable not in data.variables:
                raise ValueError(f"variant change needs a registered measured value: {change.variable}")
            value = data.variables[change.variable].value
            if change.scale is not None:
                value *= change.scale
            elif change.offset is not None:
                value += change.offset
            elif change.set is not None:
                value = change.set
            else:
                value = -value
            if not math.isfinite(value):
                raise ValueError(f"variant measurement is not finite: {change.variable}")
            data.variables[change.variable] = data.variables[change.variable].model_copy(
                update={"value": value, "source": "counterfactual variant measurement change"})
        for name in variant.rederive:
            if name not in names or name not in nominal.variables:
                raise ValueError(f"rederive needs a registered nominal measurement: {name}")
            rederive.add(name)
    for name in rederive:
        del data.variables[name]
    if not data.variables:
        raise _VariantNotEvaluable("variant rederivation needs at least one supplied measurement")
    device_report = _variant_audit(device, data, base_dir)
    device_values = {name: value.value for name, value in data.variables.items() if name in names}
    device_values.update({name: entry["value"] for name, entry in device_report.derived_variables.items()})
    for name in sorted(rederive):
        if name not in device_report.derived_variables:
            raise _VariantNotEvaluable(f"variant could not rederive requested measurement: {name}")
        data.variables[name] = nominal.variables[name].model_copy(update={
            "value": device_report.derived_variables[name]["value"], "source": "counterfactual variant model rederivation"})
    data.metadata = {**data.metadata, "variant_ids": ids, "semantics": "counterfactual data, not additional real measurements"}
    return data, device_values


def _pair_status(signature, expected):
    """Classify an evaluated multi-fault composition, never unavailable evidence."""
    failed = set(signature)
    if not failed:
        return "undetected"
    if failed == expected:
        return "ok"
    if failed < expected:
        return "masked"
    return "outside"


def _variant_result(spec, nominal, variants, baseline, base_dir):
    faults = [variant for variant in variants if variant.kind == "fault"]
    expected = {block for variant in faults for block in variant.expect_blocks}
    identity = {"id": "+".join(variant.id for variant in variants), "variant_ids": [variant.id for variant in variants],
                "kind": "fault" if faults else "benign", "expected_blocks": sorted(expected)}
    try:
        data, values = _variant_data(spec, nominal, variants, base_dir)
        report = _variant_audit(spec, data, base_dir)
    except _VariantNotEvaluable as exc:
        return {**identity, "status": "not_evaluable", "reason": str(exc), "signature": None,
                "failed_blocks": [], "audit_pass": None, "detected": False, "neutral": False,
                "expect_blocks_met": False, "pair_status": None, "ok": False,
                "generated_values": {}, "device_values": {}, "rederived_variables": []}
    signature = _signature(report)
    neutral = signature == _signature(baseline) and report.audit_pass == baseline.audit_pass
    met = expected <= signature.keys()
    pair_status = _pair_status(signature, expected) if len(faults) > 1 else None
    ok = pair_status in {"ok", "masked"} if pair_status is not None else (
        bool(signature) and met if faults else neutral
    )
    return {**identity, "status": "evaluated", "signature": signature, "failed_blocks": list(signature),
            "audit_pass": report.audit_pass, "detected": bool(signature), "neutral": neutral,
            "expect_blocks_met": met, "expected_blocks": sorted(expected), "pair_status": pair_status,
            "ok": ok,
            "generated_values": {name: value.value for name, value in data.variables.items()},
            "device_values": values, "rederived_variables": sorted({name for variant in variants for name in variant.rederive})}


def _variant_discrimination(rows, nominal, registry):
    """Compare evaluated fault singles using checked signatures and real device values."""
    faults = [row for row in rows if row["kind"] == "fault" and row["status"] == "evaluated"
              and len(row["variant_ids"]) == 1]
    pairwise = []
    signals = {}
    groups = {}
    for left, right in combinations(faults, 2):
        pair = [left["id"], right["id"]]
        if left["signature"] != right["signature"]:
            pairwise.append({"variants": pair, "separable_by": "signature", "normalized_separation": None})
            continue
        available = (set(left["device_values"]) & set(right["device_values"])) - nominal.variables.keys()
        separations = {name: abs(left["device_values"][name] - right["device_values"][name])
                       / registry.get_record(name).scale for name in available}
        ranked = sorted(separations, key=lambda name: (-separations[name], name))
        best = ranked[0] if ranked else None
        positive = best if best is not None and separations[best] > 0 else None
        pairwise.append({"variants": pair, "separable_by": positive,
                         "normalized_separation": separations.get(best)})
        group = groups.setdefault(tuple(left["signature"].items()),
                                  {"rows": {}, "separations": {}})
        group["rows"].update({left["id"]: left, right["id"]: right})
        for name, distance in separations.items():
            group["separations"][name] = max(group["separations"].get(name, 0.0), distance)
            if distance > 0:
                signal = signals.setdefault(name, {"signal": name, "separates": [],
                                                   "normalized_separation": 0.0})
                signal["separates"].append(pair)
                signal["normalized_separation"] = max(signal["normalized_separation"], distance)
    next_signal = sorted(signals.values(), key=lambda item: (
        -len(item["separates"]), -item["normalized_separation"], item["signal"]))
    indistinguishable = []
    for group in groups.values():
        members = [row for row in faults if row["id"] in group["rows"]]
        ranked = sorted(group["separations"], key=lambda name: (-group["separations"][name], name))
        best = ranked[0] if ranked and group["separations"][ranked[0]] > 0 else None
        indistinguishable.append({"variant_ids": [row["id"] for row in members],
                                  "signature": members[0]["signature"], "next_signal": best,
                                  "normalized_separation": group["separations"].get(best)})
    return {"pairwise": pairwise, "next_signal": next_signal, "indistinguishable": indistinguishable}


@residual_trace_scope
def evaluate_fault_variants(
    spec: HierarchicalAuditSpec, nominal: ObservedValuesSpec, *, pairs: bool = False,
    observed: ObservedValuesSpec | None = None, base_dir: Path | None = None,
    variant_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Generate alternate-device data, then check it with the unchanged nominal model.

    An explicit variant_ids selects one actual composition (empty means the clean
    base). This is also the finite feature-model replay entry, not a second
    physical simulator. No FlowGuard runtime dependency or reference solve.
    """
    runner = HierarchicalAuditRunner(spec, base_dir)
    baseline = runner.evaluate_observed(nominal, skip_unobserved=True, top_n_blocks=len(spec.hierarchy.blocks), _unit_factor_hints=False)
    registry = ResidualBuilder(spec.system).build_registry()
    by_id = {variant.id: variant for variant in spec.fault_variants}
    if variant_ids is not None:
        if len(set(variant_ids)) != len(variant_ids) or set(variant_ids) - by_id.keys():
            raise ValueError("selected variant ids must be unique and declared")
        group = [variant for variant in spec.fault_variants if variant.id in variant_ids]
        rows = [_variant_result(spec, nominal, group, baseline, base_dir)] if group else []
    else:
        rows = [_variant_result(spec, nominal, [variant], baseline, base_dir) for variant in spec.fault_variants]
    pair_rows = [_variant_result(spec, nominal, list(group), baseline, base_dir)
                 for group in combinations([variant for variant in spec.fault_variants if variant.kind == "fault"], 2)] if pairs else []
    matching = None
    model_miss = None
    if observed is not None:
        actual = runner.evaluate_observed(observed, skip_unobserved=True, top_n_blocks=len(spec.hierarchy.blocks), _unit_factor_hints=False)
        matching = [row["id"] for row in rows if row["kind"] == "fault" and row["status"] == "evaluated"
                    and row["signature"] == _signature(actual)]
        model_miss = not actual.audit_pass and not matching
    return {"audit_name": spec.audit_name, "nominal_audit_pass": baseline.audit_pass,
            "nominal_signature": _signature(baseline), "variants": rows, "pairs": pair_rows,
            "ok": baseline.audit_pass and all(row["ok"] for row in rows + pair_rows),
            **_variant_discrimination(rows, nominal, registry),
            "masked_pairs": list(dict.fromkeys(row["id"] for row in rows + pair_rows if row["pair_status"] == "masked")),
            "matching_variants": matching, "model_miss": model_miss,
            "claim_boundary": "Finite low-fidelity alternate-device signatures; not exhaustive faults, real observations or true-fault proof."}


__all__ = ["evaluate_fault_variants"]
