"""Interval residual status and task-local fault diagnosability."""

from __future__ import annotations

from itertools import combinations
import math
from pathlib import Path
from typing import Any

from physicsguard.schema.diagnosability import (
    DiagnosabilityRequestSpec,
    IntervalResidualSpec,
    IntervalValueSpec,
)
from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.core.residual import ResidualBuilder
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec


def _overlaps(left: IntervalValueSpec, right: IntervalValueSpec) -> bool:
    return left.lower <= right.upper and right.lower <= left.upper


def evaluate_interval_residual(
    residual: IntervalResidualSpec,
) -> dict[str, Any]:
    """Classify robust pass/fail without collapsing uncertainty to a point."""

    if residual.observed is None:
        status = "not_run"
        reason = "observed_interval_missing"
    elif (
        residual.acceptable.lower <= residual.observed.lower
        and residual.observed.upper <= residual.acceptable.upper
    ):
        status = "robust_pass"
        reason = "entire_observed_interval_is_acceptable"
    elif not _overlaps(residual.observed, residual.acceptable):
        status = "robust_fail"
        reason = "entire_observed_interval_is_outside_acceptance"
    else:
        status = "indeterminate"
        reason = "observed_interval_crosses_acceptance_boundary"
    return {
        "artifact_kind": "physicsguard_interval_residual_receipt",
        "receipt_version": "1.0",
        "residual_id": residual.residual_id,
        "status": status,
        "reason_code": reason,
        "observed_interval": (
            residual.observed.model_dump(mode="json")
            if residual.observed is not None
            else None
        ),
        "acceptable_interval": residual.acceptable.model_dump(mode="json"),
        "source_ref": residual.source_ref,
        "claim_boundary": (
            "This robust status covers only the supplied interval and "
            "acceptance interval. It does not replace the ordinary PhysicsGuard "
            "audit status or prove unmodeled uncertainty."
        ),
    }


def evaluate_diagnosability(
    request: DiagnosabilityRequestSpec,
) -> dict[str, Any]:
    """Derive pairwise distinguishability and the best declared next signal."""

    by_hypothesis = {
        item.hypothesis_id: item for item in request.fault_signatures
    }
    viable: list[str] = []
    rejected: list[str] = []
    for hypothesis_id, signature in sorted(by_hypothesis.items()):
        compatible = all(
            signal_id not in signature.predicted_intervals
            or _overlaps(
                observed,
                signature.predicted_intervals[signal_id],
            )
            for signal_id, observed in request.observed_signals.items()
        )
        (viable if compatible else rejected).append(hypothesis_id)

    pairs = tuple(combinations(viable, 2))
    signal_pair_coverage: dict[str, list[list[str]]] = {
        signal_id: [] for signal_id in sorted(request.available_signal_ids)
    }
    unresolved: list[list[str]] = []
    pair_rows: list[dict[str, Any]] = []
    for left_id, right_id in pairs:
        left = by_hypothesis[left_id].predicted_intervals
        right = by_hypothesis[right_id].predicted_intervals
        distinguishing = tuple(
            signal_id
            for signal_id in sorted(request.available_signal_ids)
            if signal_id in left
            and signal_id in right
            and not _overlaps(left[signal_id], right[signal_id])
        )
        if not distinguishing:
            unresolved.append([left_id, right_id])
        for signal_id in distinguishing:
            signal_pair_coverage[signal_id].append([left_id, right_id])
        pair_rows.append(
            {
                "hypothesis_pair": [left_id, right_id],
                "distinguishing_signal_ids": list(distinguishing),
                "status": (
                    "distinguishable"
                    if distinguishing
                    else "indistinguishable"
                ),
            }
        )

    ranked = sorted(
        (
            {
                "signal_id": signal_id,
                "newly_distinguished_pair_count": len(pair_ids),
                "hypothesis_pairs": pair_ids,
            }
            for signal_id, pair_ids in signal_pair_coverage.items()
        ),
        key=lambda item: (
            -item["newly_distinguished_pair_count"],
            item["signal_id"],
        ),
    )
    next_signal = (
        ranked[0]["signal_id"]
        if ranked and ranked[0]["newly_distinguished_pair_count"] > 0
        else ""
    )
    if len(viable) <= 1:
        status = "isolated_within_declared_signatures"
    elif not unresolved:
        status = "isolable"
    elif next_signal:
        status = "partially_isolable"
    else:
        status = "indistinguishable"
    return {
        "artifact_kind": "physicsguard_diagnosability_receipt",
        "receipt_version": "1.0",
        "diagnosis_id": request.diagnosis_id,
        "status": status,
        "viable_hypothesis_ids": viable,
        "rejected_hypothesis_ids": rejected,
        "pairwise_diagnosability": pair_rows,
        "unresolved_hypothesis_pairs": unresolved,
        "ranked_next_signal_candidates": ranked,
        "recommended_next_signal_id": next_signal,
        "claim_boundary": (
            "This result is task-local to the declared fault signatures, "
            "intervals, observations, and available signals. It does not prove "
            "that the hypotheses exhaust physical reality or identify a true "
            "fault without external evidence."
        ),
    }


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
            data, skip_unobserved=True, top_n_blocks=len(spec.hierarchy.blocks))
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
                "expect_blocks_met": False, "ok": False, "generated_values": {}, "device_values": {}, "rederived_variables": []}
    signature = _signature(report)
    neutral = signature == _signature(baseline) and report.audit_pass == baseline.audit_pass
    met = expected <= signature.keys()
    return {**identity, "status": "evaluated", "signature": signature, "failed_blocks": list(signature),
            "audit_pass": report.audit_pass, "detected": bool(signature), "neutral": neutral,
            "expect_blocks_met": met, "expected_blocks": sorted(expected),
            "ok": bool(signature) and met if faults else neutral,
            "generated_values": {name: value.value for name, value in data.variables.items()},
            "device_values": values, "rederived_variables": sorted({name for variant in variants for name in variant.rederive})}


def _indistinguishable_variants(rows, nominal, registry):
    groups = {}
    for row in rows:
        if row["kind"] == "fault" and row["status"] == "evaluated":
            groups.setdefault(tuple(row["signature"].items()), []).append(row)
    result = []
    for group in groups.values():
        if len(group) < 2:
            continue
        available = set.intersection(*(set(row["device_values"]) for row in group)) - nominal.variables.keys()
        separations = {name: (max(row["device_values"][name] for row in group)
                              - min(row["device_values"][name] for row in group)) / registry.get_record(name).scale
                       for name in available}
        ranked = sorted(separations, key=lambda name: (-separations[name], name))
        next_signal = ranked[0] if ranked and separations[ranked[0]] > 0 else None
        result.append({"variant_ids": [row["id"] for row in group], "signature": group[0]["signature"],
                       "next_signal": next_signal, "normalized_separation": separations.get(next_signal)})
    return result


def _variant_diagnosis(spec, rows, registry):
    faults = [row for row in rows if row["kind"] == "fault"]
    if any(row["status"] != "evaluated" for row in faults):
        return None
    if len(faults) < 2:
        return None
    available = sorted(set.intersection(*(set(row["device_values"]) for row in faults)))
    if not available:
        return None
    signatures = []
    for row in faults:
        intervals = {}
        for name in available:
            margin = registry.get_record(name).scale * spec.system.solver.audit_threshold
            value = row["device_values"][name]
            intervals[name] = {"lower": value - margin, "upper": value + margin}
        signatures.append({"hypothesis_id": row["id"], "predicted_intervals": intervals})
    return DiagnosabilityRequestSpec.model_validate({"diagnosis_id": spec.audit_name + "_model_variants",
        "fault_signatures": signatures, "available_signal_ids": available}).model_dump(mode="json")


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
    baseline = runner.evaluate_observed(nominal, skip_unobserved=True, top_n_blocks=len(spec.hierarchy.blocks))
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
    if observed is not None:
        actual = runner.evaluate_observed(observed, skip_unobserved=True, top_n_blocks=len(spec.hierarchy.blocks))
        matching = [row["id"] for row in rows if row["kind"] == "fault" and row["status"] == "evaluated"
                    and row["signature"] == _signature(actual)]
    return {"audit_name": spec.audit_name, "nominal_audit_pass": baseline.audit_pass,
            "nominal_signature": _signature(baseline), "variants": rows, "pairs": pair_rows,
            "ok": baseline.audit_pass and all(row["ok"] for row in rows + pair_rows),
            "indistinguishable": _indistinguishable_variants(rows, nominal, registry),
            "matching_variants": matching, "diagnose_request": _variant_diagnosis(spec, rows, registry),
            "claim_boundary": "Finite low-fidelity alternate-device signatures; not exhaustive faults, real observations or true-fault proof."}


__all__ = ["evaluate_diagnosability", "evaluate_interval_residual", "evaluate_fault_variants"]
