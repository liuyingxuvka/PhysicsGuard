"""Finite, invocation-local value/control provenance for native residuals.

This observes the ordinary Python calculation; it never substitutes numeric
objects or infers dependence from perturbations. Only native scalar expressions,
local assignments, helpers and parameter-indexed iteration are supported. An
unresolved call, source location or observed-container selection stays unknown.
"""

from __future__ import annotations

import ast
import dis
from dataclasses import dataclass, field
from pathlib import Path
import sys
from types import FrameType, FunctionType
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord


Dependencies = frozenset[str] | None
LiteralSources = tuple[Dependencies, ...] | dict[str, Dependencies]
_EMPTY: Dependencies = frozenset()
_UNKNOWN = object()
_NUMPY_SCALARS = {"interp": np.interp, "searchsorted": np.searchsorted}
_NATIVE = Path(__file__).resolve().parents[1] / "modules"
_PURE = frozenset({"abs", "all", "any", "bool", "enumerate", "float", "int", "len", "list", "max", "min", "range", "round", "str", "sum", "super", "tuple", "zip"})


def _merge(*parts: Dependencies) -> Dependencies:
    if any(part is None for part in parts):
        return None
    return frozenset().union(*parts)


def _influenced(sources: LiteralSources, controls: Dependencies) -> LiteralSources:
    if isinstance(sources, tuple):
        return tuple(_merge(source, controls) for source in sources)
    return {key: _merge(source, controls) for key, source in sources.items()}


def _key(node: ast.AST) -> tuple[int, int, int, int]:
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


def _names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for element in target.elts for name in _names(element)]
    return []


@dataclass
class _Frame:
    frame: FrameType
    node: ast.AST | None
    caller: "_Frame | None"
    site: ast.AST | None
    locals: dict[str, Dependencies] = field(default_factory=dict)
    calls: dict[tuple[int, int, int, int], Dependencies] = field(default_factory=dict)
    local_sources: dict[str, LiteralSources] = field(default_factory=dict)
    call_sources: dict[tuple[int, int, int, int], LiteralSources] = field(default_factory=dict)
    returned_sources: LiteralSources | None = None
    pending: ast.AST | None = None
    tests: dict[int, Dependencies] = field(default_factory=dict)
    inherited: Dependencies = _EMPTY
    gates: Dependencies = _EMPTY
    aggregate: Dependencies = _EMPTY
    unsupported: bool = False


class _Capture:
    def __init__(self, registry: Any, record_type: type, module: Any, vector: Any) -> None:
        self.registry = registry
        self.record_type = record_type
        self.frames: dict[int, _Frame] = {}
        self.sources: dict[str, ast.Module] = {}
        self.records: dict[int, tuple[Any, Dependencies]] = {}
        self.reads: set[str] = set()
        self.previous = sys.gettrace()
        self.previous_locals: dict[int, Any] = {}
        # Strong references to ordinary numeric constructor fields, not to raw
        # registry vectors. Identity proves a helper received this fixed table.
        self.fixed_tables: dict[int, Any] = {}
        for value in vars(module).values():
            if self._numeric_table(value) and value is not vector:
                if type(value) is not np.ndarray or not np.shares_memory(value, vector):
                    self.fixed_tables[id(value)] = value

    @staticmethod
    def _numeric_table(value: Any) -> bool:
        if type(value) is np.ndarray:
            return value.ndim in (1, 2) and value.dtype.kind in "iuf" and bool(np.isfinite(value).all())
        if type(value) not in (list, tuple) or not value:
            return False
        return all(type(item) in (int, float) and np.isfinite(item) or
                   type(item) in (list, tuple) and bool(item) and
                   all(type(number) in (int, float) and np.isfinite(number) for number in item)
                   for item in value)

    def _fixed_table(self, node: ast.AST, state: _Frame) -> bool:
        if isinstance(node, ast.Subscript):
            # Do not execute an index to infer provenance; carry selectors while
            # retaining the proven fixed origin of a row/column selection.
            return self._fixed_table(node.value, state) and self._deps(node.slice, state) is not None
        value = self._parameter_value(node, state)
        return id(value) in self.fixed_tables and self.fixed_tables[id(value)] is value

    def _numpy_scalar_call(self, node: ast.Call, state: _Frame) -> bool:
        if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
            return False
        alias = node.func.value.id
        namespace = state.frame.f_locals if alias in state.frame.f_locals else state.frame.f_globals
        if namespace.get(alias) is not np:
            return False
        if node.func.attr not in _NUMPY_SCALARS or getattr(np, node.func.attr) is not _NUMPY_SCALARS[node.func.attr]:
            return False
        count = 3 if node.func.attr == "interp" else 2 if node.func.attr == "searchsorted" else 0
        if len(node.args) != count or any(keyword.arg is None for keyword in node.keywords):
            return False
        tables = (1, 2) if count == 3 else (0,)
        if not count or not all(self._fixed_table(node.args[index], state) for index in tables):
            return False
        scalars = [arg for index, arg in enumerate(node.args) if index not in tables]
        scalars.extend(keyword.value for keyword in node.keywords)
        return all(type(self._parameter_value(arg, state)) in (int, float, str, type(None), np.float64, np.float32, np.int64, np.int32)
                   for arg in scalars)

    def _tree(self, filename: str) -> ast.Module | None:
        path = Path(filename)
        if not path.is_relative_to(_NATIVE):
            return None
        if filename not in self.sources:
            self.sources[filename] = ast.parse(path.read_text(encoding="utf-8"), filename=filename)
        return self.sources[filename]

    def _node(self, frame: FrameType, caller: _Frame | None) -> ast.AST | None:
        tree = self._tree(frame.f_code.co_filename)
        if tree is None:
            return None
        if frame.f_code.co_name in {"<listcomp>", "<genexpr>"}:
            site = self._site(caller) if caller else None
            if isinstance(site, ast.Call):
                candidates = [n for n in ast.walk(site) if isinstance(n, ast.GeneratorExp)
                              and n.lineno == frame.f_code.co_firstlineno]
                return candidates[0] if len(candidates) == 1 else None
            return site
        return next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                     and node.name == frame.f_code.co_name and node.lineno == frame.f_code.co_firstlineno), None)

    def _site(self, state: _Frame) -> ast.AST | None:
        if state.node is None:
            return None
        positions = list(state.frame.f_code.co_positions())
        offset = state.frame.f_lasti // 2
        if offset < 0 or offset >= len(positions):
            return None
        line, end_line, column, end_column = positions[offset]
        if None in (line, end_line, column, end_column):
            return None
        candidates = [node for node in ast.walk(state.node)
                      if isinstance(node, (ast.Call, ast.ListComp, ast.GeneratorExp))
                      and _key(node) == (line, column, end_line, end_column)]
        return candidates[0] if len(candidates) == 1 else None

    def _controls(self, state: _Frame, node: ast.AST | None) -> Dependencies:
        parts = [state.inherited, state.gates]
        if state.node is not None and node is not None:
            for branch in ast.walk(state.node):
                if isinstance(branch, ast.If) and branch is not node:
                    if any(child is node for item in branch.body + branch.orelse for child in ast.walk(item)):
                        parts.append(state.tests.get(id(branch)))
        return _merge(*parts)

    def _arguments(self, state: _Frame) -> None:
        caller, site = state.caller, state.site
        if caller is None:
            state.locals = {name: _EMPTY for name in state.frame.f_locals}
            return
        state.inherited = self._controls(caller, site)
        state.unsupported = caller.unsupported or caller.node is None
        if isinstance(site, (ast.ListComp, ast.GeneratorExp)):
            if len(site.generators) != 1 or any(generator.ifs for generator in site.generators):
                state.unsupported = True
            state.aggregate = _merge(*(self._deps(g.iter, caller) for g in site.generators))
            # Parameter-indexed comprehensions are supported. A selection from an
            # observation-derived container needs element provenance we do not claim.
            if isinstance(site, ast.ListComp) and state.aggregate:
                state.unsupported = True
            for generator in site.generators:
                for name in _names(generator.target):
                    state.locals[name] = state.aggregate
            for name in state.frame.f_code.co_freevars:
                state.locals[name] = caller.locals.get(name)
            return
        if not isinstance(site, ast.Call):
            state.unsupported = True
            return
        if state.frame.f_code.co_flags & (4 | 8) or any(isinstance(arg, ast.Starred) for arg in site.args):
            state.unsupported = True  # no binding claim for variadic/dynamic arguments
        if state.frame.f_code.co_freevars and state.frame.f_code is not self.record_type.__init__.__code__:
            # Only a direct invocation of this native frame's own lexical helper
            # has a proven closure binding. Escaped/external closures stay unknown.
            helper = caller.frame.f_locals.get(site.func.id) if isinstance(site.func, ast.Name) else None
            lexical = (isinstance(caller.node, ast.FunctionDef)
                       and any(node is state.node for node in caller.node.body)
                       and isinstance(helper, FunctionType)
                       and helper.__code__ is state.frame.f_code
                       and all(name in caller.locals for name in state.frame.f_code.co_freevars))
            if not lexical:
                state.unsupported = True
            else:
                for name in state.frame.f_code.co_freevars:
                    state.locals[name] = caller.locals[name]
                    if name in caller.local_sources:
                        state.local_sources[name] = caller.local_sources[name]
        self._inline_targets(caller, site)
        params = list(state.frame.f_code.co_varnames[:state.frame.f_code.co_argcount])
        if state.frame.f_code is self.record_type.__init__.__code__:
            state.locals[params.pop(0)] = _EMPTY
        elif params and params[0] in {"self", "cls"} and isinstance(site.func, ast.Attribute):
            state.locals[params.pop(0)] = self._deps(site.func.value, caller)
        elif params and params[0] in {"self", "cls"}:
            state.unsupported = True  # implicit method identity is not bound by a bare alias
        for name, value in zip(params, site.args):
            state.locals[name] = self._deps(value, caller)
            sources = self._literal_sources(value, caller)
            if sources is not None:
                state.local_sources[name] = sources
        for keyword in site.keywords:
            if keyword.arg is None:
                state.unsupported = True
            else:
                state.locals[keyword.arg] = self._deps(keyword.value, caller)
                sources = self._literal_sources(keyword.value, caller)
                if sources is not None:
                    state.local_sources[keyword.arg] = sources
        for name in state.frame.f_locals:
            state.locals.setdefault(name, _EMPTY)

    def _inline_targets(self, caller: _Frame, site: ast.AST) -> None:
        if not isinstance(caller.node, ast.FunctionDef):
            return
        for node in ast.walk(caller.node):
            if isinstance(node, ast.ListComp) and any(n is site for n in ast.walk(node.elt)):
                for generator in node.generators:
                    dependencies = self._deps(generator.iter, caller)
                    for name in _names(generator.target):
                        caller.locals[name] = _EMPTY if dependencies == _EMPTY else None
                        caller.local_sources.pop(name, None)

    def _statement(self, state: _Frame) -> ast.AST | None:
        if not isinstance(state.node, ast.FunctionDef):
            return None
        line = state.frame.f_lineno
        candidates = [node for node in ast.walk(state.node)
                      if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.If, ast.For, ast.Return))
                      and node.lineno <= line <= node.end_lineno]
        return min(candidates, key=lambda n: (n.end_lineno - n.lineno, -n.col_offset), default=None)

    def _flush(self, state: _Frame) -> None:
        node = state.pending
        if node is None:
            return
        controls = self._controls(state, node)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            dependencies = _merge(self._deps(node.value, state), controls)
            sources = self._literal_sources(node.value, state)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, (ast.Tuple, ast.List)) and isinstance(sources, tuple) and len(target.elts) == len(sources) and all(isinstance(part, ast.Name) for part in target.elts):
                    for part, source in zip(target.elts, sources):
                        state.locals[part.id] = _merge(source, controls)
                        state.local_sources.pop(part.id, None)
                    continue
                if not _names(target):
                    state.unsupported = True
                for name in _names(target):
                    if isinstance(node, ast.AugAssign):
                        dependencies = _merge(dependencies, state.locals.get(name))
                    state.locals[name] = dependencies
                    state.local_sources.pop(name, None)
                    if isinstance(target, ast.Name) and sources is not None and not isinstance(node, ast.AugAssign):
                        state.local_sources[name] = _influenced(sources, controls)
        elif isinstance(node, ast.If):
            self._branch(state, node, controls)
        elif isinstance(node, ast.For):
            dependencies = self._deps(node.iter, state)
            if dependencies:
                dependencies = None  # no per-element claim for observed containers
            for name in _names(node.target):
                state.locals[name] = _merge(dependencies, controls)
                state.local_sources.pop(name, None)

    def _branch(self, state: _Frame, node: ast.If, controls: Dependencies) -> None:
        influence = _merge(self._deps(node.test, state), controls)
        state.tests[id(node)] = influence
        # A legal flat branch still depends on the guard: record a conditional
        # reaching definition even when no branch assignment executes.
        for statement in ast.walk(node):
            targets = statement.targets if isinstance(statement, ast.Assign) else (
                [statement.target] if isinstance(statement, (ast.AnnAssign, ast.AugAssign)) else [])
            for target in targets:
                for name in _names(target):
                    state.locals[name] = _merge(state.locals.get(name, _EMPTY), influence)
                    if name in state.local_sources:
                        state.local_sources[name] = _influenced(state.local_sources[name], influence)
        if any(isinstance(n, (ast.Raise, ast.Return)) for n in ast.walk(node)):
            state.gates = _merge(state.gates, influence)

    def _deps(self, node: ast.AST | None, state: _Frame) -> Dependencies:
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            return _EMPTY
        if isinstance(node, ast.Name):
            if node.id in state.locals:
                return state.locals[node.id]
            return _EMPTY if node.id in state.frame.f_globals or node.id in _PURE else None
        if isinstance(node, ast.Attribute):
            return self._deps(node.value, state)
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
            return state.calls.get(_key(node))
        if isinstance(node, ast.Call):
            if self._numpy_scalar_call(node, state):
                return _merge(*(self._deps(arg, state) for arg in node.args),
                              *(self._deps(kw.value, state) for kw in node.keywords))
            if _key(node) in state.calls:
                return state.calls[_key(node)]
            name = ast.unparse(node.func)
            if name in _PURE or name.startswith(("math.", "np.", "numpy.")):
                return _merge(*(self._deps(arg, state) for arg in node.args),
                              *(self._deps(kw.value, state) for kw in node.keywords))
            return None
        if isinstance(node, ast.Subscript):
            sources = self._literal_sources(node.value, state)
            if isinstance(sources, dict) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                return sources.get(node.slice.value)
            if self._fixed_table(node.value, state):
                return _merge(self._deps(node.value, state), self._deps(node.slice, state))
            base = self._deps(node.value, state)
            if base:
                return None  # deliberately unsupported observed-container selection
            return _merge(base, self._deps(node.slice, state))
        if isinstance(node, ast.IfExp):
            controls = self._deps(node.test, state)
            condition = self._parameter_value(node.test, state) if controls == _EMPTY else _UNKNOWN
            if condition is not _UNKNOWN and type(condition) in (bool, int, float, str, list, tuple, dict, type(None)):
                return _merge(controls, self._deps(node.body if condition else node.orelse, state))
            # Preserve the existing conservative, finite source union for observed
            # guards; an unexecuted/unresolved helper still keeps this unknown.
            return _merge(controls, self._deps(node.body, state), self._deps(node.orelse, state))
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
                             ast.List, ast.Tuple, ast.Set, ast.Dict, ast.JoinedStr, ast.FormattedValue, ast.Slice)):
            return _merge(*(self._deps(child, state) for child in ast.iter_child_nodes(node)
                            if isinstance(child, ast.expr)))
        return None

    def _literal_sources(self, node: ast.AST, state: _Frame) -> LiteralSources | None:
        """Finite native literal fields only; never index arbitrary observed containers."""
        if isinstance(node, ast.Name):
            return state.local_sources.get(node.id)
        if isinstance(node, ast.Call):
            return state.call_sources.get(_key(node))
        if isinstance(node, ast.Tuple):
            return tuple(self._deps(element, state) for element in node.elts)
        if isinstance(node, ast.Dict) and all(isinstance(key, ast.Constant) and isinstance(key.value, str) for key in node.keys):
            return {key.value: self._deps(value, state) for key, value in zip(node.keys, node.values)}
        return None

    def _parameter_value(self, node: ast.AST, state: _Frame) -> Any:
        """Read a constant/parameter selector without evaluating Python code."""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return state.frame.f_locals.get(node.id, _UNKNOWN)
        if isinstance(node, ast.Attribute):
            base = self._parameter_value(node.value, state)
            try:
                return vars(base).get(node.attr, _UNKNOWN)
            except TypeError:
                pass
        if (isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1
                and isinstance(node.ops[0], (ast.Is, ast.IsNot))
                and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value is None):
            value = self._parameter_value(node.left, state)
            if value is not _UNKNOWN:
                return (value is None) if isinstance(node.ops[0], ast.Is) else (value is not None)
        return _UNKNOWN

    def _enter(self, frame: FrameType) -> _Frame:
        previous = self.frames.get(id(frame))
        if previous is not None and frame.f_code.co_name == "<genexpr>":
            return previous  # resume/yield belongs to the same invocation
        caller = self.frames.get(id(frame.f_back))
        state = _Frame(frame, self._node(frame, caller), caller, self._site(caller) if caller else None)
        if isinstance(state.node, (ast.ListComp, ast.GeneratorExp)):
            state.site = state.node
        self._arguments(state)
        self.frames[id(frame)] = state
        return state

    def _inline_comprehension(self, caller: _Frame, site: ast.AST) -> None:
        # Python 3.12+ inlines list comprehensions. The supported native form is
        # a scalar read/helper over fixed parameter names, not an observed list.
        if caller.node is None:
            return
        for node in ast.walk(caller.node):
            if not isinstance(node, ast.ListComp) or not any(n is site for n in ast.walk(node.elt)):
                continue
            if len(node.generators) != 1 or node.generators[0].ifs:
                caller.calls[_key(node)] = None
                continue
            iteration = self._deps(node.generators[0].iter, caller)
            element = self._deps(node.elt, caller)
            previous = caller.calls.get(_key(node), _EMPTY)
            caller.calls[_key(node)] = _merge(previous, element) if iteration == _EMPTY else None

    def _returned(self, state: _Frame, value: Any) -> Dependencies:
        frame = state.frame
        if frame.f_code is self.registry.get_index.__func__.__code__ and frame.f_locals.get("self") is self.registry:
            name = frame.f_locals["name"]
            self.reads.add(name)
            return _merge(frozenset({name}), state.locals.get("name"), state.inherited)
        if frame.f_code is self.registry.get_record.__func__.__code__:
            return _merge(state.locals.get("name"), state.inherited)  # selection only, not the observed scalar
        if frame.f_code is self.record_type.__init__.__code__:
            dependencies = None if state.unsupported else _merge(state.locals.get("value"), state.inherited)
            record = frame.f_locals["self"]
            self.records[id(record)] = (record, dependencies)
            return dependencies
        if state.node is None or state.unsupported:
            return None
        self._flush(state)
        if isinstance(state.node, (ast.ListComp, ast.GeneratorExp)):
            if isinstance(state.node, ast.GeneratorExp) and dis.opname[frame.f_code.co_code[frame.f_lasti]].startswith("RETURN_"):
                # An exhausted parameter-indexed generator executes no element.
                # Empty sum is structurally constant; nonempty yields have already
                # accumulated their actual sources in this invocation's aggregate.
                return _merge(state.aggregate, state.inherited)
            return _merge(state.aggregate, state.inherited, self._deps(state.node.elt, state))
        if isinstance(state.pending, ast.Return):
            sources = self._literal_sources(state.pending.value, state)
            controls = self._controls(state, state.pending)
            if sources is not None:
                state.returned_sources = _influenced(sources, controls)
            return _merge(self._deps(state.pending.value, state), self._controls(state, state.pending))
        return None

    def trace(self, frame: FrameType, event: str, value: Any):
        if self.previous is not None:
            old = self.previous if event == "call" else self.previous_locals.get(id(frame))
            if old is not None:
                self.previous_locals[id(frame)] = old(frame, event, value)
        if event == "call":
            self._enter(frame)
        state = self.frames.get(id(frame))
        if state is None:
            return self.trace
        if event == "line":
            statement = self._statement(state)
            if statement is not state.pending:
                self._flush(state)
                state.pending = statement
                if statement is not None:
                    for node in ast.walk(statement):
                        if isinstance(node, (ast.Call, ast.ListComp, ast.GeneratorExp)):
                            state.calls.pop(_key(node), None)
                            state.call_sources.pop(_key(node), None)
        elif event == "return":
            dependencies = self._returned(state, value)
            if state.caller is not None and state.site is not None:
                state.caller.calls[_key(state.site)] = dependencies
                state.caller.call_sources.pop(_key(state.site), None)
                if state.returned_sources is not None:
                    state.caller.call_sources[_key(state.site)] = state.returned_sources
                state.caller.aggregate = _merge(state.caller.aggregate, dependencies)
                self._inline_comprehension(state.caller, state.site)
            if frame.f_code.co_name != "<genexpr>":
                self.frames.pop(id(frame), None)
                self.previous_locals.pop(id(frame), None)
        return self.trace


# Dependency lists are reused only inside one outer command; verdicts are never cached.
from contextvars import ContextVar
from functools import wraps
from dataclasses import fields, is_dataclass

_TRACE_REUSE = ContextVar('physicsguard_residual_trace_reuse', default=None)


def residual_trace_scope(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        if _TRACE_REUSE.get() is not None:
            return function(*args, **kwargs)
        token = _TRACE_REUSE.set({})
        try:
            return function(*args, **kwargs)
        finally:
            _TRACE_REUSE.reset(token)
    return scoped


def _trace_value(value):
    """Copy all key material, including complete arrays; unknown objects disable reuse."""
    if type(value) is float:
        return ('float', value.hex())
    if type(value) in (str, bytes, bool, int, type(None)):
        return (type(value), value)
    if type(value) is np.ndarray:
        if value.dtype.hasobject:
            return _UNKNOWN
        return ('array', value.dtype.str, value.shape, value.tobytes())
    if isinstance(value, np.generic):
        return ('scalar', value.dtype.str, value.tobytes())
    if type(value) is VariableRecord:
        # Its fixed eight-field schema avoids reflective dataclass walks for every module.
        parts = tuple(_trace_value(item) for item in
                      (value.name, value.unit, value.lower_bound, value.upper_bound,
                       value.initial_guess, value.scale, value.source_component, value.local_name))
        return _UNKNOWN if any(item is _UNKNOWN for item in parts) else (VariableRecord, parts)
    if is_dataclass(value) and not isinstance(value, type):
        parts = tuple((item.name, _trace_value(getattr(value, item.name))) for item in fields(value))
    elif type(value) is dict:
        parts = tuple((key, _trace_value(item)) for key, item in sorted(value.items(), key=lambda item: repr(item[0])))
    elif type(value) in (list, tuple):
        parts = tuple((index, _trace_value(item)) for index, item in enumerate(value))
    else:
        return _UNKNOWN
    if any(item is _UNKNOWN for _, item in parts):
        return _UNKNOWN
    return (type(value), parts)


def _trace_key(module, registry, record_type, vector):
    # A constructor table that aliases observations is not a fixed input.
    if any(value is vector or (type(value) is np.ndarray and type(vector) is np.ndarray and np.shares_memory(value, vector))
           for value in vars(module).values()):
        return None
    key = (type(module), module.component_id, repr(sorted(module.parameters.items())))
    attributes = _trace_value(vars(module))
    layout = _trace_value(vars(registry))
    if attributes is _UNKNOWN or layout is _UNKNOWN:
        return None
    return (key, attributes, type(registry), layout, module.residuals.__func__, record_type)


def _trace_inputs(names, vector, registry):
    return tuple((name, _trace_value(vector[registry.get_index(name)])) for name in sorted(names))


def module_residual_dependencies(module: Any, vector: Any, registry: Any, record_type: type):
    """Run the real method once; pair each actual returned record with its sources.

    Private strong references retain constructor identities for this invocation.
    No cache survives the command. A custom method cannot be licensed from an empty owned
    variable list, and the former trace is restored even on errors or reentry.
    """
    filename = Path(module.residuals.__code__.co_filename)
    if not filename.is_relative_to(_NATIVE):
        records = module.residuals(vector, registry)
        return records, [None for record in records], False
    cache = _TRACE_REUSE.get()
    key = _trace_key(module, registry, record_type, vector) if cache is not None else None
    if key is not None:
        for previous, dependencies, no_reads in cache.get(key, ()):
            if previous == _trace_inputs((name for name, value in previous), vector, registry):
                records = module.residuals(vector, registry)
                if len(records) == len(dependencies):
                    if len({id(record) for record in records}) != len(records):
                        return records, [None for record in records], no_reads
                    return records, list(dependencies), no_reads
                break
    capture = _Capture(registry, record_type, module, vector)
    try:
        sys.settrace(capture.trace)
        records = module.residuals(vector, registry)
    finally:
        sys.settrace(capture.previous)
    dependencies = []
    for record in records:
        entry = capture.records.get(id(record))
        dependencies.append(entry[1] if entry is not None and entry[0] is record else None)
    if len({id(record) for record in records}) != len(records):
        dependencies = [None for record in records]
    if key is not None and key == _trace_key(module, registry, record_type, vector):
        cache.setdefault(key, []).append((_trace_inputs(capture.reads, vector, registry), tuple(dependencies), not capture.reads))
    return records, dependencies, not capture.reads
