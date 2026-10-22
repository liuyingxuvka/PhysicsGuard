"""Finite native alternate-device fault signatures; independent of parent state."""

from pathlib import Path

from flowguard.kit import Feature, feature_conformance, feature_explorer, feature_variants

from physicsguard.core.diagnosability import evaluate_fault_variants
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values


MODEL_ID = "fault_variants"
PARENT = "interval_diagnosability"
ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/hierarchical/heated_tank"
SPEC = load_hierarchical_audit_spec(EXAMPLE / "heated_tank.yaml")
NOMINAL = load_observed_values(EXAMPLE / "measured_k30.yaml")

FEATURES = tuple(
    # Heater + inlet uses the biased Tin when rederiving T_current, closing the
    # nominal thermal residual and masking the inlet code. CLI pairs keep it.
    Feature(variant.id, variant.kind == "fault", codes=tuple(variant.expect_blocks) if variant.kind == "fault" else (),
            apply=lambda selected, name=variant.id: selected + (name,), exclusive=variant.id == "inlet_temp_offset")
    for variant in SPEC.fault_variants
)

IMPLEMENTED_BY = {"EvaluateFaultVariants": "src/physicsguard/core/diagnosability.py:evaluate_fault_variants"}
TESTED_BY = {
    "clean_input_accepted": ["tests/test_fault_variants.py:test_clean_nominal_is_accepted_without_mutating_inputs"],
    "each_defect_rejected": ["tests/test_fault_variants.py:test_each_declared_tank_fault_is_detected_with_direct_block_evidence"],
    "every_defect_reported": ["tests/test_fault_variants.py:test_combined_faults_report_every_direct_failure"],
    "benign_features_neutral": ["tests/test_fault_variants.py:test_benign_default_parameter_override_keeps_the_verdict"],
}


def build_explorer():
    return feature_explorer(FEATURES, max_features=2)


def broken_variants():
    return feature_variants(FEATURES, max_features=2)


def _review(selected):
    result = evaluate_fault_variants(SPEC, NOMINAL, variant_ids=selected, base_dir=EXAMPLE)
    if not result["variants"]:
        return result["nominal_audit_pass"], tuple(result["nominal_signature"])
    row = result["variants"][0]
    if row["status"] != "evaluated":
        raise ValueError(row["reason"])
    return row["audit_pass"], tuple(row["failed_blocks"])


def conformance():
    return feature_conformance(FEATURES, lambda: (), _review, max_features=2)
