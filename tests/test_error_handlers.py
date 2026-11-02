"""One route per function: an error must reach the caller, never turn into a quiet default or a skip.

The inventory below lists every exception handler in src/ and scripts/ that does not re-raise,
keyed by file, function and caught types, with the reason it may stay. The scan is computed from
the source, so a new swallowing handler fails this test until someone states why it may exist.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap

import pytest

from conftest import ROOT, run_cli

VISIBLE = "the error becomes a reported error (finding, blocked/not_evaluable status or exit 2) carrying its text"

NON_RAISING_HANDLERS = {
    "src/physicsguard/cli.py:testfile_manifest_command:ValueError":
        "os.path.relpath has no answer across Windows drives; the absolute path is the same file, not a second route",
    "src/physicsguard/cli.py:_print_validation_tree:(OSError, ValueError)":
        "a text view of a finished report; it prints 'unavailable audit' and the report already holds the input finding",
    "src/physicsguard/cli.py:main:Exception": "the single command boundary: prints 'physicsguard error: ...' and exits 2",
    "src/physicsguard/core/_residual_dependencies.py:_Capture._parameter_value:TypeError":
        "an object without attributes cannot be read by the tracer; its value stays unknown, so no read is claimed",
    "src/physicsguard/core/data_file_manifest.py:_infer_scalar_type:ValueError":
        "type inference asks 'does this text parse as int/float?'; a parse failure is the answer, not an error",
    "src/physicsguard/core/data_file_manifest.py:_parse_time_seconds:ValueError":
        "time inference tries the declared formats in turn; a cell that parses as none is reported as untyped",
    "src/physicsguard/core/data_file_manifest.py:_typed_time_value:ValueError":
        "a time cell that is not numeric keeps its text value; type inference, not a second route",
    "src/physicsguard/core/diagnosability.py:_variant_result:_VariantNotEvaluable":
        "the variant is reported with status not_evaluable and the reason",
    "src/physicsguard/core/hierarchy.py:_bounded_root:(ValueError, KeyError, ArithmeticError, IndexError)":
        "a relation that has no unique root in the variable's bounds derives nothing; the variable stays listed as unobserved",
    "src/physicsguard/core/hierarchy.py:_observed_resolution:(ValueError, KeyError, IndexError, OverflowError, ZeroDivisionError)":
        "a finite-difference step outside a relation's domain gives no sample; without samples the resolution prints unknown",
    "src/physicsguard/core/hierarchy.py:_unit_factor_followups:(ValueError, KeyError, IndexError, ArithmeticError)":
        "a unit-factor hypothesis outside a relation's domain is not evidence for a hint; other errors reach the caller",
    "src/physicsguard/core/model_dataset_validation.py:_contract_findings:Exception": VISIBLE,
    "src/physicsguard/core/model_dataset_validation.py:_load_validation_input:Exception": VISIBLE,
    "src/physicsguard/core/parameter_coverage.py:check_field_mappings:ValueError": VISIBLE,
    "src/physicsguard/core/predictive_rollout.py:_load_series:Exception": VISIBLE,
    "src/physicsguard/core/residual.py:ResidualBuilder.residual_scale_defaults:ValueError":
        "a text parameter that is not a number is not perturbed; its scale contribution stays unclaimed",
    "src/physicsguard/core/residual.py:ResidualBuilder.residual_scale_defaults:(ValueError, KeyError, IndexError, ArithmeticError)":
        "a perturbed parameter a native module refuses cannot license a scale claim (the scale stays unknown); other errors reach the caller",
    "src/physicsguard/core/test_file_contract.py:check_test_file_contract:(ValueError, OSError, KeyError)": VISIBLE,
    "src/physicsguard/core/validation_adequacy.py:contract_input_error_path:Exception":
        "only picks which file an already reported loading error names: the contract itself when it cannot be read",
    "src/physicsguard/core/validation_adequacy.py:resolve_validation_roles:Exception":
        "the same contract is loaded by load_contract_field_mappings, which reports the failure once with its path",
    "src/physicsguard/core/validation_adequacy.py:load_contract_field_mappings:Exception": VISIBLE,
    "src/physicsguard/core/validation_adequacy.py:_load_or_find:Exception": VISIBLE,
    "src/physicsguard/core/validation_depth.py:_contract_series:Exception": VISIBLE,
    "src/physicsguard/core/validation_depth.py:_dataset_identity_result:Exception": VISIBLE,
    "src/physicsguard/core/validation_depth.py:_residual_series_result:Exception": VISIBLE,
    "src/physicsguard/core/validation_depth.py:_load_series:Exception": VISIBLE,
}


def _non_raising_handlers() -> dict[str, int]:
    found: dict[str, int] = {}
    paths = sorted((ROOT / "src" / "physicsguard").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py"))
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()

        def visit(node, names):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit(child, names + [child.name])
                    continue
                if isinstance(child, ast.ExceptHandler):
                    body = ast.Module(body=child.body, type_ignores=[])
                    if not any(isinstance(item, ast.Raise) for item in ast.walk(body)):
                        caught = ast.unparse(child.type) if child.type else "BARE"
                        key = f"{relative}:{'.'.join(names) or '<module>'}:{caught}"
                        found[key] = found.get(key, 0) + 1
                visit(child, names)

        visit(ast.parse(path.read_text(encoding="utf-8")), [])
    return found


def test_every_non_raising_handler_is_listed_with_a_reason() -> None:
    found = _non_raising_handlers()
    assert "BARE" not in " ".join(found), "a bare except swallows everything, including KeyboardInterrupt"
    assert sorted(set(found) - set(NON_RAISING_HANDLERS)) == [], "new handlers that do not re-raise: state why or raise"
    assert sorted(set(NON_RAISING_HANDLERS) - set(found)) == [], "listed handlers that no longer exist: drop them"


def _inject_inside(monkeypatch, outer_owner, outer_name, inner_owner, inner_name):
    """Make inner raise RuntimeError, but only while outer runs; everything else keeps its real behaviour."""
    active = {"on": False}
    outer, inner = getattr(outer_owner, outer_name), getattr(inner_owner, inner_name)

    def wrapped_outer(*args, **kwargs):
        active["on"] = True
        try:
            return outer(*args, **kwargs)
        finally:
            active["on"] = False

    def wrapped_inner(*args, **kwargs):
        if active["on"]:
            raise RuntimeError("injected failure")
        return inner(*args, **kwargs)

    monkeypatch.setattr(outer_owner, outer_name, wrapped_outer)
    monkeypatch.setattr(inner_owner, inner_name, wrapped_inner)


def _evaluate(audit, observation):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    shower = ROOT / "examples" / "hierarchical" / "shower_mix"
    runner = HierarchicalAuditRunner(load_hierarchical_audit_spec(shower / audit), shower)
    return runner.evaluate_observed(load_observed_values(shower / observation))


def test_an_error_inside_a_unit_factor_trial_fails_the_evaluation(monkeypatch) -> None:
    from physicsguard.core import hierarchy
    from physicsguard.core.residual import ResidualBuilder

    _inject_inside(monkeypatch, hierarchy, "_unit_factor_followups", ResidualBuilder, "diagnostic_residual_records")
    with pytest.raises(RuntimeError, match="injected failure"):
        _evaluate("audit.yaml", "observed_q_kw.yaml")


def test_an_error_inside_a_scale_replay_fails_the_evaluation(monkeypatch) -> None:
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.modules.physical.thermal import CoolantHeatBalanceModule

    _inject_inside(monkeypatch, ResidualBuilder, "residual_scale_defaults", CoolantHeatBalanceModule, "residuals")
    with pytest.raises(RuntimeError, match="injected failure"):
        _evaluate("audit.yaml", "observed_ai.yaml")


def test_an_injected_failure_reaches_the_command_exit_code(tmp_path) -> None:
    script = tmp_path / "inject.py"
    script.write_text(textwrap.dedent("""
        import sys
        from physicsguard.core import hierarchy
        from physicsguard.core.residual import ResidualBuilder
        from physicsguard import cli

        probe, records, inside = hierarchy._unit_factor_followups, ResidualBuilder.diagnostic_residual_records, []

        def watched_probe(*args, **kwargs):
            inside.append(True)
            try:
                return probe(*args, **kwargs)
            finally:
                inside.pop()

        def broken_records(self, *args, **kwargs):
            if inside:
                raise RuntimeError("injected failure")
            return records(self, *args, **kwargs)

        hierarchy._unit_factor_followups = watched_probe
        ResidualBuilder.diagnostic_residual_records = broken_records
        sys.exit(cli.main(sys.argv[1:]))
    """), encoding="utf-8")
    shower = ROOT / "examples" / "hierarchical" / "shower_mix"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    result = subprocess.run([sys.executable, str(script), "hierarchy", "evaluate", str(shower / "audit.yaml"),
                             str(shower / "observed_q_kw.yaml")], capture_output=True, text=True, env=env)
    assert result.returncode == 2, result.stdout
    assert "physicsguard error: injected failure" in result.stderr


def test_a_failing_git_listing_is_reported_not_replaced(monkeypatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("portable_model_headers", ROOT / "scripts" / "portable_model_headers.py")
    headers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(headers)

    def no_git(*args, **kwargs):
        raise OSError("git is not installed")

    monkeypatch.setattr(headers.subprocess, "run", no_git)
    with pytest.raises(RuntimeError, match="cannot list the tracked example files.*git is not installed"):
        headers.tracked_example_yaml_files(ROOT)


def test_no_test_declares_a_skip() -> None:
    names = {"skip", "skipif", "xfail", "importorskip"}
    offenders = []
    for path in sorted((ROOT / "tests").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in names:
                offenders.append(f"{path.name}:{node.lineno} {node.attr}")
    assert offenders == []


def test_a_test_that_ends_skipped_fails_the_run(tmp_path) -> None:
    (tmp_path / "test_hidden.py").write_text(textwrap.dedent("""
        import pytest

        def _load():
            try:
                raise OSError("fixture file missing")
            except OSError:
                pytest.skip("input not available")

        def test_quietly_skipped():
            _load()
    """), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "tests") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no_skips",
                             str(tmp_path / "test_hidden.py")], capture_output=True, text=True, env=env, cwd=tmp_path)
    assert result.returncode == 1, result.stdout
    assert "1 failed" in result.stdout and "skipped" not in result.stdout.splitlines()[-1]
