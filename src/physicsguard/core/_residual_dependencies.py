"""Finite, invocation-local value/control provenance for native residuals.

This observes the ordinary Python calculation; it never substitutes numeric
objects or infers dependence from perturbations. Only native scalar expressions,
local assignments, helpers and parameter-indexed iteration are supported. An
unresolved call, source location or observed-container selection stays unknown.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import sys
from types import FrameType
from typing import Any


Dependencies = frozenset[str] | None
_EMPTY: Dependencies = frozenset()
_NATIVE = Path(__file__).resolve().parents[1] / "modules"
_PURE = frozenset({"abs", "all", "any", "bool", "enumerate", "float", "int", "len", "list", "max", "min", "range", "round", "str", "sum", "super", "tuple", "zip"})


def _merge(*parts: Dependencies) -> Dependencies:
    if any(part is None for part in parts):
        return None
    return frozenset().union(*parts)


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
    pending: ast.AST | None = None
    tests: dict[int, Dependencies] = field(default_factory=dict)
    inherited: Dependencies = _EMPTY
    gates: Dependencies = _EMPTY
    aggregate: Dependencies = _EMPTY
    unsupported: bool = False


class _Capture:
    def __init__(self, registry: Any, record_type: type) -> None:
        self.registry = registry
        self.record_type = record_type
        self.frames: dict[int, _Frame] = {}
        self.sources: dict[str, ast.Module] = {}
        self.records: dict[int, tuple[Any, Dependencies]] = {}
        self.reads: set[str] = set()
        self.previous = sys.gettrace()
        self.previous_locals: dict[int, Any] = {}

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
            state.unsupported = True  # arbitrary helper closure bindings are not inferred
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
        for keyword in site.keywords:
            if keyword.arg is None:
                state.unsupported = True
            else:
                state.locals[keyword.arg] = self._deps(keyword.value, caller)
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
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not _names(target):
                    state.unsupported = True
                for name in _names(target):
                    if isinstance(node, ast.AugAssign):
                        dependencies = _merge(dependencies, state.locals.get(name))
                    state.locals[name] = dependencies
        elif isinstance(node, ast.If):
            self._branch(state, node, controls)
        elif isinstance(node, ast.For):
            dependencies = self._deps(node.iter, state)
            if dependencies:
                dependencies = None  # no per-element claim for observed containers
            for name in _names(node.target):
                state.locals[name] = _merge(dependencies, controls)

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
            if _key(node) in state.calls:
                return state.calls[_key(node)]
            name = ast.unparse(node.func)
            if name in _PURE or name.startswith(("math.", "np.", "numpy.")):
                return _merge(*(self._deps(arg, state) for arg in node.args),
                              *(self._deps(kw.value, state) for kw in node.keywords))
            return None
        if isinstance(node, ast.Subscript):
            base = self._deps(node.value, state)
            if base:
                return None  # deliberately unsupported observed-container selection
            return _merge(base, self._deps(node.slice, state))
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.IfExp,
                             ast.List, ast.Tuple, ast.Set, ast.Dict, ast.JoinedStr, ast.FormattedValue, ast.Slice)):
            return _merge(*(self._deps(child, state) for child in ast.iter_child_nodes(node)
                            if isinstance(child, ast.expr)))
        return None

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
            return _merge(state.aggregate, state.inherited, self._deps(state.node.elt, state))
        if isinstance(state.pending, ast.Return):
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
        elif event == "return":
            dependencies = self._returned(state, value)
            if state.caller is not None and state.site is not None:
                state.caller.calls[_key(state.site)] = dependencies
                state.caller.aggregate = _merge(state.caller.aggregate, dependencies)
                self._inline_comprehension(state.caller, state.site)
            if frame.f_code.co_name != "<genexpr>":
                self.frames.pop(id(frame), None)
                self.previous_locals.pop(id(frame), None)
        return self.trace


def module_residual_dependencies(module: Any, vector: Any, registry: Any, record_type: type):
    """Run the real method once; pair each actual returned record with its sources.

    Private strong references retain constructor identities for this invocation.
    No cache survives it. A custom method cannot be licensed from an empty owned
    variable list, and the former trace is restored even on errors or reentry.
    """
    filename = Path(module.residuals.__code__.co_filename)
    if not filename.is_relative_to(_NATIVE):
        records = module.residuals(vector, registry)
        return records, [None for record in records], False
    capture = _Capture(registry, record_type)
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
    return records, dependencies, not capture.reads
