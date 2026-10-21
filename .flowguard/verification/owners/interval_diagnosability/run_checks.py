"""Run PhysicsGuard interval-diagnosability model checks and replay them on the real code."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

from flowguard import FunctionResult
from flowguard.explorer import Explorer
from flowguard.review import review_scenarios

ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / ".flowguard/models/owners/interval_diagnosability/model.py"
IMPLEMENTED_BY = {
    "EvaluateInterval": "src/physicsguard/core/diagnosability.py:evaluate_interval_residual",
    "EvaluateDiagnosability": "src/physicsguard/core/diagnosability.py:evaluate_diagnosability",
}
TESTED_BY = {
    "no_interval_collapse": [
        "tests/test_diagnosability.py:test_interval_residual_preserves_robust_statuses",
    ],
    "no_true_fault_claim": [
        "tests/test_diagnosability.py:test_diagnosability_reports_pairwise_evidence_and_next_signal",
        "tests/test_diagnosability.py:test_task_model_diagnose_cli_exits_1_when_hypotheses_cannot_be_separated",
    ],
}


def _load_model():
    spec = importlib.util.spec_from_file_location("physicsguard_interval_diagnosability_model", MODEL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load model {MODEL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


model = _load_model()


def _interval(observed):
    return {
        "residual_id": "conformance",
        "observed": observed,
        "acceptable": {"lower": -1.0, "upper": 1.0},
        "source_ref": "conformance:interval",
    }


def _signatures(*speeds):
    return {
        "diagnosis_id": "conformance",
        "fault_signatures": [
            {"hypothesis_id": f"h{index}", "predicted_intervals": {"speed": {"lower": low, "upper": low + 1.0}}}
            for index, low in enumerate(speeds)
        ],
        "available_signal_ids": ["speed"],
    }


# Scenario name -> (interval residual input, diagnosability request) for the real code.
REAL_CASES = {
    "PGD01_inside_pass": (_interval({"lower": -0.2, "upper": 0.4}), _signatures(0.0, 5.0)),
    "PGD02_crossing_indeterminate": (_interval({"lower": 0.5, "upper": 1.5}), _signatures(0.0, 0.5, 5.0)),
    "PGD03_indistinguishable_visible": (_interval(None), _signatures(0.0, 0.0)),
}


def conformance() -> list[str]:
    """Run each scenario's inputs through the real diagnosability code; return the mismatches."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from physicsguard.core.diagnosability import evaluate_diagnosability, evaluate_interval_residual
    from physicsguard.schema.diagnosability import DiagnosabilityRequestSpec, IntervalResidualSpec

    mismatches = []
    for scenario in model.scenarios():
        residual, request = REAL_CASES[scenario.name]
        run = model.workflow().execute(model.DiagnosticState(), scenario.external_input_sequence[0])
        path = run.completed_paths[0]
        labels = [step.label for step in path.trace.steps]
        interval = evaluate_interval_residual(IntervalResidualSpec.model_validate(residual))
        diagnosis = evaluate_diagnosability(DiagnosabilityRequestSpec.model_validate(request))
        if f"interval_{interval['status']}" not in labels:
            mismatches.append(f"{scenario.name}: real interval {interval['status']!r}, model labels {labels}")
        if f"diagnosis_{diagnosis['status']}" not in labels:
            mismatches.append(f"{scenario.name}: real diagnosis {diagnosis['status']!r}, model labels {labels}")
        if bool(diagnosis["recommended_next_signal_id"]) != bool(path.state.recommended_signal):
            mismatches.append(
                f"{scenario.name}: real next signal {diagnosis['recommended_next_signal_id']!r}, "
                f"model {path.state.recommended_signal!r}"
            )
    return mismatches


class _CollapsesCrossingInterval(model.EvaluateInterval):
    def apply(self, request, state):
        for result in super().apply(request, state):
            if request.observed_interval == "crossing":
                result = replace(result, new_state=replace(result.new_state, robust_status="robust_pass"))
            yield result


class _LicensesTrueFault(model.EvaluateDiagnosability):
    def apply(self, request, state):
        for result in super().apply(request, state):
            yield replace(result, new_state=replace(result.new_state, truth_claim_licensed=True))


def broken_variants():
    """Known-bad variants: name -> (blocks, invariant that must catch it)."""

    return {
        "crossing_interval_collapsed": (
            (_CollapsesCrossingInterval(), model.EvaluateDiagnosability()),
            "no_interval_collapse",
        ),
        "diagnosability_licenses_true_fault": (
            (model.EvaluateInterval(), _LicensesTrueFault()),
            "no_true_fault_claim",
        ),
    }


def missed_variants() -> list[str]:
    from flowguard import Workflow

    inputs = tuple(scenario.external_input_sequence[0] for scenario in model.scenarios())
    missed = []
    for name, (blocks, invariant) in broken_variants().items():
        report = Explorer(
            workflow=Workflow(blocks, name=name),
            initial_states=(model.DiagnosticState(),),
            external_inputs=inputs,
            invariants=model.INVARIANTS,
        ).explore()
        if invariant not in {item.invariant_name for item in report.violations}:
            missed.append(f"{name}: {invariant} did not fail")
    return missed


def main() -> int:
    report = review_scenarios(model.scenarios())
    mismatches = conformance()
    missed = missed_variants()
    print(
        json.dumps(
            {
                "artifact_kind": "physicsguard_interval_diagnosability_model_report",
                "status": "pass" if report.ok and not mismatches and not missed else "fail",
                "scenario_count": len(report.results),
                "claim_boundary": (
                    "The model covers only the declared interval and "
                    "task-local diagnosability scenarios."
                ),
            },
            sort_keys=True,
        )
    )
    print(f"conformance: {len(REAL_CASES) - len(mismatches)}/{len(REAL_CASES)} scenarios match the real code")
    for line in mismatches:
        print(f"  mismatch: {line}")
    print(f"known-bad variants: {len(broken_variants()) - len(missed)}/{len(broken_variants())} caught")
    for line in missed:
        print(f"  missed: {line}")
    return 0 if report.ok and not mismatches and not missed else 1


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
