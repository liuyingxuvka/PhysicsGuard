from __future__ import annotations

import json
from pathlib import Path

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "assumptions"


def run_report(name: str):
    spec = load_system_spec(EXAMPLES / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    reporter = DiagnosticReporter()
    return reporter, reporter.generate(spec, builder, result, top_n=50)


def test_normal_diagnostic_json_includes_assumptions_section() -> None:
    reporter, report = run_report("variable_assumption.yaml")
    data = reporter.to_dict(report)
    assert "assumptions" in data
    assert data["assumptions"]["active_count"] == 1
    assert data["assumptions"]["cards"][0]["id"] == "assume_coolant_inlet_temperature"


def test_high_impact_and_active_assumption_warnings_appear() -> None:
    _, report = run_report("variable_assumption.yaml")
    assert "assumptions were used" in report.warnings
    assert "high-impact assumptions were used" in report.warnings
    assert report.assumptions.confidence_factor == pytest.approx(0.75)


def test_proposed_assumption_warning_appears_and_not_applied() -> None:
    _, report = run_report("proposed_assumption.yaml")
    assert report.assumptions.proposed_count == 1
    assert report.assumptions.cards[0].application == "not_applied_proposed"
    assert "proposed assumptions were not applied" in report.warnings


def test_parameter_override_warning_appears() -> None:
    _, report = run_report("parameter_override_warning.yaml")
    assert report.assumptions.cards[0].application == "parameter_override"
    assert "one or more explicit parameters were overridden by assumptions" in report.warnings


def test_confidence_factor_is_computed_and_output_is_json_serializable() -> None:
    reporter, report = run_report("parameter_assumption.yaml")
    assert report.assumptions.total_confidence_penalty == pytest.approx(0.02)
    assert report.assumptions.confidence_factor == pytest.approx(0.98)
    json.dumps(reporter.to_dict(report))


def test_empty_assumptions_section_for_existing_example() -> None:
    spec = load_system_spec(ROOT / "examples" / "dummy_system.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert report.assumptions.active_count == 0
    assert report.assumptions.cards == []
