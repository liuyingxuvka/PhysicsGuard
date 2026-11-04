"""One route per function: an error must reach the caller, never turn into a quiet default or a skip.

The inventory below lists every exception handler in src/ and scripts/ that can finish without
raising, keyed by file, function and caught types, with the number of such handlers there and the
reason they may stay. The scan is computed from the source: a handler counts as re-raising only
when every path through it ends in a raise, so `if strict: raise` followed by `return None` is a
swallowing handler. A new one fails this test until someone states why it may exist.

The tool's own probes (unit-factor hints, scale replays, resolution samples, bounded root search)
skip exactly a relation's DomainRefusal; the injection tests below show every other error type
reaching the caller and the command's exit code.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest

from conftest import ROOT, run_cli

VISIBLE = "the error becomes a reported error (finding, blocked/not_evaluable status or exit 2) carrying its text"

NON_RAISING_HANDLERS = {
    # key: (number of such handlers, why they may finish without raising)
    "src/physicsguard/cli.py:testfile_manifest_command:ValueError": (2,
        "os.path.relpath has no answer across Windows drives; the absolute path is the same file, not a second route"),
    "src/physicsguard/cli.py:_print_validation_tree:(OSError, ValueError)": (1,
        "a text view of a finished report; it prints 'unavailable audit' and the report already holds the input finding"),
    "src/physicsguard/cli.py:main:Exception": (1, "the single command boundary: prints 'physicsguard error: ...' and exits 2"),
    "src/physicsguard/core/_residual_dependencies.py:_Capture._parameter_value:TypeError": (1,
        "an object without attributes cannot be read by the tracer; its value stays unknown, so no read is claimed"),
    "src/physicsguard/core/data_file_manifest.py:_infer_scalar_type:ValueError": (2,
        "type inference asks 'does this text parse as int/float?'; a parse failure is the answer, not an error"),
    "src/physicsguard/core/data_file_manifest.py:_parse_time_seconds:ValueError": (2,
        "time inference tries the declared formats in turn; a cell that parses as none is reported as untyped"),
    "src/physicsguard/core/data_file_manifest.py:_typed_time_value:ValueError": (1,
        "a time cell that is not numeric keeps its text value; type inference, not a second route"),
    "src/physicsguard/core/diagnosability.py:_variant_result:_VariantNotEvaluable": (1,
        "the variant is reported with status not_evaluable and the reason"),
    "src/physicsguard/core/hierarchy.py:_bounded_root:(DomainRefusal, ArithmeticError)": (1,
        "sampling a relation across a variable's whole bound window meets refusals and divisions by zero; "
        "then no unique root is claimed and the variable stays listed as unobserved; any other error reaches the caller"),
    "src/physicsguard/core/hierarchy.py:_observed_resolution:DomainRefusal": (2,
        "a finite-difference step the relation refuses gives no sample; without samples the resolution prints unknown"),
    "src/physicsguard/core/hierarchy.py:_unit_factor_followups:DomainRefusal": (1,
        "a unit-factor hypothesis the relation refuses is not evidence for a hint; any other error reaches the caller"),
    "src/physicsguard/core/model_dataset_validation.py:_contract_findings:Exception": (1, VISIBLE),
    "src/physicsguard/core/model_dataset_validation.py:_load_validation_input:Exception": (1, VISIBLE),
    "src/physicsguard/core/parameter_coverage.py:check_field_mappings:ValueError": (2, VISIBLE),
    "src/physicsguard/core/predictive_rollout.py:_load_series:Exception": (1, VISIBLE),
    "src/physicsguard/core/residual.py:ResidualBuilder.residual_scale_defaults:ValueError": (1,
        "a text parameter that is not a number is not perturbed; its scale contribution stays unclaimed"),
    "src/physicsguard/core/residual.py:ResidualBuilder.residual_scale_defaults:DomainRefusal": (1,
        "a perturbed parameter the module refuses cannot license a scale claim (the scale prints as unavailable)"),
    "src/physicsguard/core/test_file_contract.py:check_test_file_contract:(ValueError, OSError, KeyError)": (1, VISIBLE),
    "src/physicsguard/core/validation_adequacy.py:contract_input_error_path:Exception": (1,
        "only picks which file an already reported loading error names: the contract itself when it cannot be read"),
    "src/physicsguard/core/validation_adequacy.py:resolve_validation_roles:Exception": (1,
        "the same contract is loaded by load_contract_field_mappings, which reports the failure once with its path"),
    "src/physicsguard/core/validation_adequacy.py:load_contract_field_mappings:Exception": (1, VISIBLE),
    "src/physicsguard/core/validation_adequacy.py:_load_or_find:Exception": (1, VISIBLE),
    "src/physicsguard/core/validation_depth.py:_contract_series:Exception": (1, VISIBLE),
    "src/physicsguard/core/validation_depth.py:_dataset_identity_result:Exception": (1, VISIBLE),
    "src/physicsguard/core/validation_depth.py:_residual_series_result:Exception": (2, VISIBLE),
    "src/physicsguard/core/validation_depth.py:_load_series:Exception": (1, VISIBLE),
    "src/physicsguard/modules/registry.py:describe_module_type:(ValueError, TypeError, KeyError)": (1,
        "describe retries with a synthetic value for the parameter the error names; an error naming no fillable "
        "parameter, or the 64th retry, is raised with its text"),
    "src/physicsguard/modules/registry.py:describe_module_type:KeyError": (1,
        "describe adds the external variable a 'unknown variable: a.b' error names and retries; any other KeyError, "
        "or the 64th retry, is raised"),
}


def _outcome(statements, in_loop=False):
    """(can finish normally, can leave by return/break/continue) for a statement list."""
    falls, leaves = True, False
    for statement in statements:
        if not falls:
            break
        statement_falls, statement_leaves = _statement_outcome(statement, in_loop)
        leaves |= statement_leaves
        falls = statement_falls
    return falls, leaves


def _statement_outcome(node, in_loop):
    if isinstance(node, ast.Raise):
        return False, False
    if isinstance(node, ast.Return):
        return False, True
    if isinstance(node, (ast.Break, ast.Continue)):
        return False, not in_loop
    if isinstance(node, ast.If):
        (body_falls, body_leaves), (else_falls, else_leaves) = _outcome(node.body, in_loop), _outcome(node.orelse, in_loop)
        return body_falls or else_falls, body_leaves or else_leaves
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return _outcome(node.body, in_loop)
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        # The body may run zero times; break/continue inside it stay inside the loop.
        _falls, body_leaves = _outcome(node.body, True)
        _else_falls, else_leaves = _outcome(node.orelse, in_loop)
        return True, body_leaves or else_leaves
    if isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
        (body_falls, body_leaves), (else_falls, else_leaves) = _outcome(node.body, in_loop), _outcome(node.orelse, in_loop)
        falls, leaves = body_falls and else_falls, body_leaves or else_leaves
        for handler in node.handlers:
            handler_falls, handler_leaves = _outcome(handler.body, in_loop)
            falls, leaves = falls or handler_falls, leaves or handler_leaves
        if node.finalbody:
            final_falls, final_leaves = _outcome(node.finalbody, in_loop)
            falls, leaves = falls and final_falls, leaves or final_leaves
        return falls, leaves
    if isinstance(node, ast.Match):
        return True, any(_outcome(case.body, in_loop)[1] for case in node.cases)
    # Plain statements, and nested def/class bodies, which do not run here.
    return True, False


def reraises_on_every_path(handler: ast.ExceptHandler) -> bool:
    return _outcome(handler.body) == (False, False)


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
                    if not reraises_on_every_path(child):
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
    counts = {key: sites for key, (sites, _reason) in NON_RAISING_HANDLERS.items()}
    assert found == counts, "a listed function gained or lost a handler that does not re-raise"
    assert all(reason.strip() for _sites, reason in NON_RAISING_HANDLERS.values())


def _handler(text):
    source = "for item in items:\n    try:\n        work()\n" + textwrap.indent(textwrap.dedent(text).strip(), "    ") + "\n"
    return next(node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ExceptHandler))


@pytest.mark.parametrize("text, reraises", [
    ("except KeyError:\n    raise", True),
    ("except KeyError as exc:\n    note(exc)\n    raise ValueError('named') from exc", True),
    ("except KeyError:\n    if strict:\n        raise\n    return None", False),
    ("except KeyError:\n    if strict:\n        raise\n    else:\n        raise ValueError('other')", True),
    ("except KeyError:\n    if quiet:\n        return None\n    raise", False),
    ("except KeyError:\n    for row in rows:\n        raise", False),
    ("except KeyError:\n    for row in rows:\n        continue\n    raise", True),
    ("except KeyError:\n    def later():\n        raise\n    return later", False),
    ("except KeyError:\n    continue", False),
    ("except KeyError:\n    try:\n        cleanup()\n    except OSError:\n        pass\n    raise", True),
    ("except KeyError:\n    with lock:\n        return None", False),
    ("except KeyError:\n    with lock:\n        raise", True),
])
def test_a_handler_reraises_only_when_every_path_raises(text, reraises) -> None:
    assert reraises_on_every_path(_handler(text)) is reraises


# Every error type a programming fault commonly raises; none of them is a relation's refusal.
FAULTS = [RuntimeError, KeyError, IndexError, ZeroDivisionError, OverflowError, ValueError, TypeError, AttributeError]
SHOWER = ROOT / "examples" / "hierarchical" / "shower_mix"


def _inject_inside(monkeypatch, outer_owner, outer_name, inner_owner, inner_name, error, when=None):
    """Make inner raise `error`, but only while outer runs (and `when(*args)` holds); otherwise unchanged."""
    active = {"on": False, "raised": 0}
    outer, inner = getattr(outer_owner, outer_name), getattr(inner_owner, inner_name)

    def wrapped_outer(*args, **kwargs):
        active["on"] = True
        try:
            return outer(*args, **kwargs)
        finally:
            active["on"] = False

    def wrapped_inner(*args, **kwargs):
        if active["on"] and (when is None or when(*args, **kwargs)):
            active["raised"] += 1
            raise error("injected failure")
        return inner(*args, **kwargs)

    monkeypatch.setattr(outer_owner, outer_name, wrapped_outer)
    monkeypatch.setattr(inner_owner, inner_name, wrapped_inner)
    return active


def _evaluate(audit, observation):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    runner = HierarchicalAuditRunner(load_hierarchical_audit_spec(SHOWER / audit), SHOWER)
    return runner.evaluate_observed(load_observed_values(SHOWER / observation))


def _hint_trial(monkeypatch, error):
    from physicsguard.core import hierarchy
    from physicsguard.core.residual import ResidualBuilder

    return _inject_inside(monkeypatch, hierarchy, "_unit_factor_followups", ResidualBuilder,
                          "diagnostic_residual_records", error)


def _perturbed_scale_replay(monkeypatch, error):
    """Fail only the replays with a perturbed parameter (plain dicts), not the baseline replay."""
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.modules.registry import ModuleRegistry

    return _inject_inside(monkeypatch, ResidualBuilder, "residual_scale_defaults", ModuleRegistry, "create", error,
                          when=lambda _self, _type, _id, parameters: type(parameters) is dict)


def _resolution_sample(monkeypatch, error):
    from physicsguard.core import hierarchy

    return _inject_inside(monkeypatch, hierarchy, "_observed_resolution", hierarchy, "_evaluate_record", error)


@pytest.mark.parametrize("error", FAULTS, ids=lambda error: error.__name__)
def test_an_error_inside_a_unit_factor_trial_fails_the_evaluation(monkeypatch, error) -> None:
    _hint_trial(monkeypatch, error)
    with pytest.raises(error, match="injected failure"):
        _evaluate("audit.yaml", "observed_q_unmapped.yaml")


@pytest.mark.parametrize("error", FAULTS, ids=lambda error: error.__name__)
def test_an_error_inside_a_scale_replay_fails_the_evaluation(monkeypatch, error) -> None:
    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.modules.physical.thermal import CoolantHeatBalanceModule

    _inject_inside(monkeypatch, ResidualBuilder, "residual_scale_defaults", CoolantHeatBalanceModule, "residuals", error)
    with pytest.raises(error, match="injected failure"):
        _evaluate("audit_default_scales.yaml", "observed_ai_half.yaml")


@pytest.mark.parametrize("error", FAULTS, ids=lambda error: error.__name__)
def test_an_error_inside_a_perturbed_scale_replay_fails_the_evaluation(monkeypatch, error) -> None:
    _perturbed_scale_replay(monkeypatch, error)
    with pytest.raises(error, match="injected failure"):
        _evaluate("audit_default_scales.yaml", "observed_ai_half.yaml")


@pytest.mark.parametrize("error", FAULTS, ids=lambda error: error.__name__)
def test_an_error_inside_a_resolution_sample_fails_the_evaluation(monkeypatch, error) -> None:
    _resolution_sample(monkeypatch, error)
    with pytest.raises(error, match="injected failure"):
        _evaluate("audit.yaml", "observed_ai.yaml")


@pytest.mark.parametrize("error", [RuntimeError, KeyError, IndexError, ValueError, TypeError, AttributeError],
                         ids=lambda error: error.__name__)
def test_an_error_inside_a_root_search_reaches_the_caller(error) -> None:
    from physicsguard.core.hierarchy import _bounded_root

    def relation(_value):
        raise error("injected failure")

    with pytest.raises(error, match="injected failure"):
        _bounded_root(relation, SimpleNamespace(lower_bound=0.0, upper_bound=1.0))


@pytest.mark.parametrize("error", ["refusal", ZeroDivisionError, OverflowError],
                         ids=["DomainRefusal", "ZeroDivisionError", "OverflowError"])
def test_a_root_search_that_meets_a_refusal_or_a_division_claims_no_root(error) -> None:
    from physicsguard.core.hierarchy import _bounded_root
    from physicsguard.modules.base import DomainRefusal

    raised = DomainRefusal if error == "refusal" else error

    def relation(value):
        if value < 0.5:
            raise raised("outside")
        return value - 0.75

    assert _bounded_root(relation, SimpleNamespace(lower_bound=0.0, upper_bound=1.0)) is None
    assert _bounded_root(lambda value: value - 0.75, SimpleNamespace(lower_bound=0.0, upper_bound=1.0)) == pytest.approx(0.75)


def test_a_relation_refusal_inside_the_probes_is_skipped_and_the_verdict_stands(monkeypatch) -> None:
    from physicsguard.modules.base import DomainRefusal

    hint = _hint_trial(monkeypatch, DomainRefusal)
    report = _evaluate("audit.yaml", "observed_q_unmapped.yaml")
    assert hint["raised"] > 0 and report.audit_pass is False
    assert not any(row.family == "unit_conversion" for row in report.bug_family_followups)
    monkeypatch.undo()
    scale = _perturbed_scale_replay(monkeypatch, DomainRefusal)
    resolution = _resolution_sample(monkeypatch, DomainRefusal)
    report = _evaluate("audit_default_scales.yaml", "observed_ai_half.yaml")
    assert scale["raised"] > 0 and resolution["raised"] > 0 and report.audit_pass is True


def test_the_hint_and_the_scale_appear_without_injection() -> None:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner

    report = _evaluate("audit.yaml", "observed_q_unmapped.yaml")
    assert [row.trigger for row in report.bug_family_followups if row.family == "unit_conversion"] == [
        "Trying heater.Q_dot_W: multiply by 1000 makes every checked residual in hot_branch pass."]
    text = run_cli("hierarchy", "evaluate", str(SHOWER / "audit_default_scales.yaml"), str(SHOWER / "observed_ai_half.yaml"))
    assert "(default scale)" in text.stdout and "unavailable" not in text.stdout


_CLI_INJECTION = """
import sys
from physicsguard.core import hierarchy
from physicsguard.core.residual import ResidualBuilder
from physicsguard.modules.registry import ModuleRegistry
from physicsguard import cli

error = {error}
inside = []

def watch(owner, name):
    original = getattr(owner, name)
    def watched(*args, **kwargs):
        inside.append(name)
        try:
            return original(*args, **kwargs)
        finally:
            inside.pop()
    setattr(owner, name, watched)

def fail_when(owner, name, probe, condition=lambda *args: True):
    original = getattr(owner, name)
    def failing(*args, **kwargs):
        if probe in inside and condition(*args):
            raise error("injected failure")
        return original(*args, **kwargs)
    setattr(owner, name, failing)

watch(hierarchy, "_unit_factor_followups")
watch(ResidualBuilder, "residual_scale_defaults")
fail_when(ResidualBuilder, "diagnostic_residual_records", "_unit_factor_followups")
fail_when(ModuleRegistry, "create", "residual_scale_defaults", lambda _self, _type, _id, parameters: type(parameters) is dict)
sys.exit(cli.main(sys.argv[1:]))
"""


@pytest.mark.parametrize("error", ["RuntimeError", "KeyError", "IndexError", "ZeroDivisionError", "ValueError"])
@pytest.mark.parametrize("audit, observation", [("audit.yaml", "observed_q_unmapped.yaml"),
                                                ("audit_default_scales.yaml", "observed_ai_half.yaml")],
                         ids=["unit_factor_hint", "scale_replay"])
def test_an_injected_failure_reaches_the_command_exit_code(tmp_path, error, audit, observation) -> None:
    script = tmp_path / "inject.py"
    script.write_text(_CLI_INJECTION.format(error=error), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    result = subprocess.run([sys.executable, str(script), "hierarchy", "evaluate", str(SHOWER / audit),
                             str(SHOWER / observation)], capture_output=True, text=True, env=env)
    assert result.returncode == 2, result.stdout
    assert "physicsguard error: " in result.stderr and "injected failure" in result.stderr


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


SKIP_NAMES = {"skip", "skipif", "xfail", "importorskip", "skipTest", "skipIf", "skipUnless", "expectedFailure",
              "SkipTest", "collect_ignore", "collect_ignore_glob", "pytest_ignore_collect"}


def _declared_skips(path):
    offenders = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names = []
        if isinstance(node, ast.Attribute):
            names = [node.attr]
        elif isinstance(node, ast.Name):
            names = [node.id]
        elif isinstance(node, (ast.ImportFrom, ast.Import)):
            names = [alias.name.rsplit(".", 1)[-1] for alias in node.names]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names = [node.name]
        offenders += [f"{path.name}:{node.lineno} {name}" for name in names if name in SKIP_NAMES]
    return offenders


def test_no_test_declares_a_skip() -> None:
    offenders = [item for path in sorted((ROOT / "tests").glob("*.py")) if path.name != "test_error_handlers.py"
                 for item in _declared_skips(path)]
    assert offenders == []


@pytest.mark.parametrize("source", [
    "import pytest\npytest.importorskip('no_such_module_xyz')\n",
    "from pytest import importorskip\nimportorskip('no_such_module_xyz')\n",
    "from pytest import skip as later\n",
    "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.skipTest('no input')\n",
    "collect_ignore = ['test_other.py']\n",
])
def test_the_static_scan_sees_every_way_to_declare_a_skip(tmp_path, source) -> None:
    path = tmp_path / "test_sample.py"
    path.write_text(source, encoding="utf-8")
    assert _declared_skips(path) != []


def _run_hidden(tmp_path, source):
    (tmp_path / "test_hidden.py").write_text(textwrap.dedent(source), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "tests") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no_skips",
                           str(tmp_path / "test_hidden.py")], capture_output=True, text=True, env=env, cwd=tmp_path)


@pytest.mark.parametrize("source", [
    """
    import pytest

    def _load():
        try:
            raise OSError("fixture file missing")
        except OSError:
            pytest.skip("input not available")

    def test_quietly_skipped():
        _load()
    """,
    """
    import unittest

    class Hidden(unittest.TestCase):
        def test_quietly_skipped(self):
            self.skipTest("input not available")
    """,
], ids=["runtime_skip", "unittest_skipTest"])
def test_a_test_that_ends_skipped_fails_the_run(tmp_path, source) -> None:
    result = _run_hidden(tmp_path, source)
    assert result.returncode == 1, result.stdout
    assert "1 failed" in result.stdout and "skipped" not in result.stdout.splitlines()[-1]


@pytest.mark.parametrize("source", [
    """
    from pytest import importorskip
    importorskip("no_such_module_xyz")

    def test_never_collected():
        assert True
    """,
    """
    import pytest
    pytest.skip("input not available", allow_module_level=True)

    def test_never_collected():
        assert True
    """,
], ids=["importorskip_at_collection", "module_level_skip"])
def test_a_file_skipped_while_it_is_collected_fails_the_run(tmp_path, source) -> None:
    result = _run_hidden(tmp_path, source)
    assert result.returncode != 0, result.stdout
    last = result.stdout.splitlines()[-1]
    assert "error" in last and "skipped" not in last, result.stdout
    assert "skipped while it was collected" in result.stdout


def _numeric_example_parameters(description):
    parameters = dict(description["parameters"]["synthetic_example"])
    for key, value in description["parameters"]["optional"].items():
        if key not in parameters and isinstance(value, (int, float)) and not isinstance(value, bool):
            parameters[key] = value
    return parameters


def test_every_native_range_check_refuses_with_a_domain_refusal() -> None:
    """The scale replay perturbs numeric parameters; a refusal it meets must be a DomainRefusal, not a plain error."""
    from physicsguard.core.registry import VariableRecord, VariableRegistry
    from physicsguard.modules.base import DomainRefusal
    from physicsguard.modules.registry import default_module_registry, describe_module_type

    modules = default_module_registry()
    offenders, perturbed = [], 0
    for module_type in sorted(modules.registered_types()):
        description = describe_module_type(module_type, modules)
        parameters = _numeric_example_parameters(description)
        registry = VariableRegistry()
        for variable in modules.create(module_type, "example", parameters).declare_variables():
            registry.add_variable(variable)
        for name in description["description_context"]["synthetic_external_variables"]:
            registry.add_variable(VariableRecord(name, None, -1e6, 1e6, 1.0, 1.0))
        for key, value in parameters.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            step = 1 if isinstance(value, int) else max(abs(value) * 1e-4, 1e-4)
            for candidate in (value + step, value - step, 0.0, -abs(value) - 1.0):
                trial = {**parameters, key: candidate}
                perturbed += 1
                try:
                    modules.create(module_type, "example", trial).residuals(registry.initial_vector(), registry)
                except DomainRefusal:
                    continue
                except Exception as exc:  # collected and asserted below
                    offenders.append(f"{module_type}.{key}={candidate!r}: {type(exc).__name__}: {exc}")
    assert perturbed > 1000
    assert offenders == []


def test_the_unit_factor_hint_also_runs_on_a_partial_snapshot(tmp_path) -> None:
    """An unobserved, underivable variable elsewhere must not stop the hint search (it once raised KeyError, swallowed)."""
    import yaml

    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    data = yaml.safe_load((SHOWER / "audit.yaml").read_text(encoding="utf-8"))
    data["system"]["components"].append({"id": "unrelated", "type": "MappedSignalModule"})
    data["hierarchy"]["blocks"][0]["components"].append("unrelated")
    audit = tmp_path / "audit.yaml"
    audit.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    runner = HierarchicalAuditRunner(load_hierarchical_audit_spec(audit), SHOWER)
    report = runner.evaluate_observed(load_observed_values(SHOWER / "observed_q_unmapped.yaml"), skip_unobserved=True)
    assert "unrelated.value" in report.missing_required_variables
    assert [row.trigger for row in report.bug_family_followups if row.family == "unit_conversion"] == [
        "Trying heater.Q_dot_W: multiply by 1000 makes every checked residual in hot_branch pass."]
