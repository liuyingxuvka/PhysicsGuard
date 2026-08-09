from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import yaml
import pytest


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"
RUNTIME_REGISTRY = ROOT / ".physicsguard" / "module_runtime_port_contracts.yaml"
COMPILER_PATH = ROOT / "scripts" / "compile_module_semantics.py"
RUNTIME_BUILDER_PATH = ROOT / "scripts" / "build_module_runtime_port_contracts.py"


@lru_cache(maxsize=1)
def _load_compiler() -> ModuleType:
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(
        "physicsguard_module_semantics_compiler_test",
        COMPILER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(text: str) -> dict:
    result = yaml.load(text, Loader=yaml.CSafeLoader)
    assert isinstance(result, dict)
    return result


def _records(payload: dict) -> dict[str, dict]:
    return {item["module_type"]: item for item in payload["module_records"]}


def _record_chunks(text: str) -> dict[str, str]:
    starts = list(re.finditer(r"(?m)^- module_type: ([^\r\n]+)\r?$", text))
    chunks: dict[str, str] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        chunks[match.group(1).strip()] = text[match.start():end]
    return chunks


def _at_path(value: dict, path: str):
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def test_compiler_is_deterministic_and_leaves_non_batch_records_byte_exact() -> None:
    compiler = _load_compiler()

    first_ledger, first_runtime, first_report = compiler.compile_outputs(ROOT, LEDGER)
    second_ledger, second_runtime, second_report = compiler.compile_outputs(ROOT, LEDGER)

    assert first_ledger == second_ledger
    assert first_runtime == second_runtime
    assert first_report == second_report
    assert first_report["compiled_module_count"] == 78
    assert first_report["gold_module_count"] == 4
    assert first_report["exact_scenario_role_module_count"] == 15
    assert first_report["mechanical_draft_module_count"] == 22
    assert first_report["source_first_reconstruction_module_count"] == 37
    assert first_report["source_semantic_ir_bound_count"] == 78
    assert first_report["source_semantic_ir_error_count"] == 0
    assert {
        item["module_type"]
        for item in first_report["modules"]
        if item["formula_authority"] is not None
    } == compiler.FORMULA_MODULES
    assert first_report["runtime_registry"]["resolved_count"] == 78
    assert first_report["runtime_registry"]["unresolved_count"] == 74

    before_chunks = _record_chunks(compiler._read_exact(LEDGER))
    after_chunks = _record_chunks(first_ledger)
    assert before_chunks.keys() == after_chunks.keys()
    for module_type in sorted(before_chunks.keys() - compiler.COMPILED_MODULES):
        assert after_chunks[module_type] == before_chunks[module_type]


def test_compiler_binds_only_observed_source_and_authorized_port_projections() -> None:
    compiler = _load_compiler()
    before = _records(_payload(LEDGER.read_text(encoding="utf-8")))
    compiled_ledger, _, report = compiler.compile_outputs(ROOT, LEDGER)
    after = _records(_payload(compiled_ledger))
    runtime_payload = compiler.runtime_ports.build_registry_payload(ROOT, LEDGER)
    runtime_entries = {
        item["module_type"]: item for item in runtime_payload["modules"]
    }

    for item in report["modules"]:
        module_type = item["module_type"]
        record = after[module_type]
        assert record["source_semantic_ir"] == {
            "schema": compiler.SOURCE_IR_SCHEMA,
            "fingerprint": item["source_semantic_ir_fingerprint"],
        }
        assert record["function_block"]["role_authority"] == (
            compiler.runtime_ports.resolved_role_authority_binding(
                runtime_entries[module_type]
            )
        )
        if item["batch"] == "gold":
            assert item["runtime_role_authority"] == (
                "intrinsic_project_formula_contract"
            )
            assert record["function_block"]["role_authority"][
                "direction_scope"
            ] == "intrinsic_module_contract"
            assert record["function_block"]["role_authority"][
                "relation_directionality"
            ] == "directed"
        elif item["batch"] == "exact_scenario_role":
            assert item["runtime_role_authority"] == (
                "canonical_reviewed_scenario_role"
            )
            assert item["formula_authority"] == (
                f".physicsguard/module_formulas/{module_type}.yaml"
            )
            resource = record["bindings"]["resources"]
            assert len(resource) == 1
            assert resource[0]["kind"] == "physical_formula"
            assert resource[0]["implementation_binding"] == {
                **record["bindings"]["implementation"],
                "source_semantic_ir_fingerprint": item[
                    "source_semantic_ir_fingerprint"
                ],
            }
            assert resource[0]["parameter_semantics"] == record[
                "function_block"
            ]["configuration"]
            assert len(resource[0]["dimensional_derivations"]) == len(
                record["residual_definitions"]
            )
            assert record["bindings"]["oracle"]["authority"]["path"] == item[
                "formula_authority"
            ]
            assert record["bindings"]["oracle"]["independent_from_implementation"] is True
        elif item["batch"] == "mechanical_draft_pending_independent_review":
            assert item["runtime_role_authority"] == "mechanical_draft_formula_role"
            assert item["formula_authority"] == (
                f".physicsguard/module_formulas/{module_type}.yaml"
            )
            resource = record["bindings"]["resources"]
            assert len(resource) == 1
            assert resource[0]["kind"] == "mechanical_semantic_draft"
            assert resource[0]["authoring_status"] == (
                "mechanical_draft_pending_independent_review"
            )
            assert resource[0]["separate_review_status"] == "pending"
            assert resource[0]["physical_claim_licensed"] is False
            assert record["bindings"]["oracle"]["independent_from_implementation"] is False
            assert record["bindings"]["oracle"]["independence_status"] == (
                "pending_separate_review"
            )
            assert record["bindings"]["oracle"]["physical_claim_licensed"] is False
            role_authority = record["function_block"]["role_authority"]
            assert role_authority["direction_scope"] == (
                "exact_instantiation_mechanical_draft"
            )
            assert role_authority["relation_directionality"] == "direction_neutral"
        else:
            assert item["batch"] == (
                "source_first_reconstruction_pending_independent_review"
            )
            assert item["runtime_role_authority"] == "source_first_formula_role"
            assert item["formula_authority"] == (
                f".physicsguard/module_formulas/{module_type}.yaml"
            )
            resource = record["bindings"]["resources"]
            assert len(resource) == 1
            assert resource[0]["kind"] == "source_first_semantic_reconstruction"
            assert resource[0]["authoring_status"] == (
                "source_first_reconstruction_pending_independent_review"
            )
            assert resource[0]["separate_review_status"] == "pending"
            assert resource[0]["physical_claim_licensed"] is False
            if module_type == "MappedSignalModule":
                assert record["bindings"]["oracle"]["disposition"] == (
                    "not_applicable"
                )
                assert record["bindings"]["oracle"]["kind"] == (
                    "declaration_only_no_equation"
                )
                assert record["bindings"]["oracle"]["applicability_kind"] == (
                    "declaration_only_no_equation"
                )
            else:
                assert record["bindings"]["oracle"][
                    "independent_from_implementation"
                ] is False
                assert record["bindings"]["oracle"]["independence_status"] == (
                    "pending_separate_review"
                )
                assert record["bindings"]["oracle"][
                    "physical_claim_licensed"
                ] is False
            role_authority = record["function_block"]["role_authority"]
            assert role_authority["direction_scope"] == (
                "exact_instantiation_source_first_reconstruction"
            )
            assert role_authority["relation_directionality"] == "direction_neutral"
        assert record["semantic_review"]["status"] == "pending"
        assert record["semantic_review"]["license"] == "unlicensed"
        assert record["semantic_review"]["subject_fingerprint"] == (
            compiler.ledger_checker._record_fingerprint(record)
        )
        for path in compiler.PRESERVED_DOMAIN_PATHS:
            assert _at_path(record, path) == _at_path(before[module_type], path)
        assert all(
            compiler._path_is_compiler_owned(path)
            for path in item["changed_paths"]
        )


def test_compiler_refuses_unresolved_source_semantics(monkeypatch) -> None:
    compiler = _load_compiler()
    before = _records(_payload(LEDGER.read_text(encoding="utf-8")))[
        "BrakeSimpleModule"
    ]
    runtime_payload = compiler.runtime_ports.build_registry_payload(ROOT, LEDGER)
    entry = next(
        item
        for item in runtime_payload["modules"]
        if item["module_type"] == "BrakeSimpleModule"
    )
    monkeypatch.setattr(
        compiler.ledger_checker,
        "_source_residual_contract",
        lambda *_: {
            "semantic_ir_errors": ["unresolved helper"],
            "semantic_ir_fingerprint": None,
        },
    )

    try:
        compiler._synchronize_source_observations(
            ROOT, copy.deepcopy(before), "BrakeSimpleModule", entry
        )
    except ValueError as exc:
        assert "recursive source semantic IR is unresolved" in str(exc)
    else:
        raise AssertionError("the compiler accepted unresolved source semantics")


def test_all_22_mechanical_draft_oracle_cases_are_executable_and_unlicensed() -> None:
    compiler = _load_compiler()
    compiled_ledger, _, report = compiler.compile_outputs(ROOT, LEDGER)
    records = _records(_payload(compiled_ledger))
    mechanical_reports = [
        item
        for item in report["modules"]
        if item["batch"] == "mechanical_draft_pending_independent_review"
    ]

    assert len(mechanical_reports) == 22
    for item in mechanical_reports:
        module_type = item["module_type"]
        formula, relative_path, resource_sha256 = compiler._load_scenario_formula(
            ROOT, module_type
        )
        record = records[module_type]
        assert formula["physical_claim_licensed"] is False
        assert formula["separate_review_status"] == "pending"
        assert record["bindings"]["resources"][0]["sha256"] == resource_sha256
        assert record["bindings"]["resources"][0]["path"] == relative_path
        expressions = {
            expression["name"]: expression["expression"]
            for expression in record["bindings"]["oracle"]["expressions"]
        }
        cases = record["bindings"]["oracle"]["cases"]
        assert len(cases) >= 2
        for case in cases:
            tolerance = float(case["tolerance"])
            for residual_name, expected in case["expected"].items():
                actual = compiler.ledger_checker._restricted_expression(
                    expressions[residual_name], case["inputs"]
                )
                assert float(actual) == pytest.approx(
                    float(expected), abs=tolerance, rel=0.0
                )


def _scenario_compile_with_formula(
    monkeypatch,
    module_type: str,
    mutate,
):
    compiler = _load_compiler()
    before = _records(_payload(LEDGER.read_text(encoding="utf-8")))[module_type]
    runtime_payload = compiler.runtime_ports.build_registry_payload(ROOT, LEDGER)
    entry = next(
        item for item in runtime_payload["modules"] if item["module_type"] == module_type
    )
    formula, path, sha256 = compiler._load_scenario_formula(ROOT, module_type)
    attacked = copy.deepcopy(formula)
    mutate(attacked)
    original_loader = compiler._load_scenario_formula

    def load_formula(root: Path, selected: str):
        if selected == module_type:
            return attacked, path, sha256
        return original_loader(root, selected)

    monkeypatch.setattr(compiler, "_load_scenario_formula", load_formula)
    return compiler._synchronize_source_observations(
        ROOT, copy.deepcopy(before), module_type, entry
    )


def test_compiler_rejects_missing_formula_parameter(monkeypatch) -> None:
    def mutate(formula: dict) -> None:
        formula["configuration"] = [
            item for item in formula["configuration"] if item["name"] != "n_cells"
        ]

    try:
        _scenario_compile_with_formula(
            monkeypatch, "CellVoltageStackVoltageModule", mutate
        )
    except ValueError as exc:
        assert "source expression dependencies are unresolved" in str(exc)
    else:
        raise AssertionError("the compiler accepted a missing required formula parameter")


def test_compiler_rejects_wrong_formula_parameter_default(monkeypatch) -> None:
    def mutate(formula: dict) -> None:
        next(
            item
            for item in formula["configuration"]
            if item["name"] == "residual_scale"
        )["default"] = 0.02

    try:
        _scenario_compile_with_formula(monkeypatch, "EfficiencyModule", mutate)
    except ValueError as exc:
        assert "required/default semantics disagree" in str(exc)
    else:
        raise AssertionError("the compiler accepted a wrong source parameter default")


def test_compiler_rejects_wrong_formula_port_unit(monkeypatch) -> None:
    def mutate(formula: dict) -> None:
        formula["scenario_inputs"][0]["dimension"] = "power"
        formula["scenario_inputs"][0]["unit"] = "W"

    try:
        _scenario_compile_with_formula(monkeypatch, "ForceVelocityPowerModule", mutate)
    except ValueError as exc:
        assert "scenario port direction/unit is stale" in str(exc)
    else:
        raise AssertionError("the compiler accepted a formula/runtime unit mismatch")


def test_compiler_rejects_missing_protected_denominator(monkeypatch) -> None:
    def mutate(formula: dict) -> None:
        formula["constraints"]["evaluation"] = []

    try:
        _scenario_compile_with_formula(monkeypatch, "EfficiencyModule", mutate)
    except ValueError as exc:
        assert "protected denominator evaluation predicate is missing" in str(exc)
    else:
        raise AssertionError("the compiler accepted a missing denominator protection")


def test_compiler_rejects_missing_source_intermediate(monkeypatch) -> None:
    def mutate(formula: dict) -> None:
        formula["residuals"][0]["source_intermediates"] = [
            item
            for item in formula["residuals"][0]["source_intermediates"]
            if item["symbol"] != "expected"
        ]

    try:
        _scenario_compile_with_formula(monkeypatch, "IdealGasDensityModule", mutate)
    except ValueError as exc:
        assert "source expression dependencies are unresolved" in str(exc)
    else:
        raise AssertionError("the compiler accepted a missing source intermediate")


def test_apply_then_check_is_idempotent_in_an_isolated_copy(tmp_path: Path) -> None:
    ledger = tmp_path / "module_equation_ledger.yaml"
    runtime_registry = tmp_path / "module_runtime_port_contracts.yaml"
    ledger.write_bytes(LEDGER.read_bytes())
    runtime_registry.write_bytes(RUNTIME_REGISTRY.read_bytes())
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    apply_result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_PATH),
            "--ledger",
            str(ledger),
            "--runtime-output",
            str(runtime_registry),
            "--apply",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert apply_result.returncode == 0, apply_result.stderr
    assert json.loads(apply_result.stdout)["status"] == "pass"
    first_ledger = ledger.read_bytes()
    first_runtime = runtime_registry.read_bytes()

    check_result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_PATH),
            "--ledger",
            str(ledger),
            "--runtime-output",
            str(runtime_registry),
            "--check",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert check_result.returncode == 0, check_result.stderr
    assert json.loads(check_result.stdout)["status"] == "pass"
    assert ledger.read_bytes() == first_ledger
    assert runtime_registry.read_bytes() == first_runtime


def test_runtime_registry_builder_is_check_only(tmp_path: Path) -> None:
    output = tmp_path / "must_not_be_written.yaml"
    result = subprocess.run(
        [sys.executable, str(RUNTIME_BUILDER_PATH), "--output", str(output)],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert not output.exists()
    assert "compile_module_semantics.py --apply" in result.stderr
