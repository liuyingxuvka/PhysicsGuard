from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import inspect
import json
import os
import re
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_module_runtime_port_contracts as runtime_ports
import check_module_equation_ledger as ledger_checker


DEFAULT_LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"
DEFAULT_RUNTIME_REGISTRY = ROOT / ".physicsguard" / "module_runtime_port_contracts.yaml"
COMPILER_IDENTITY = "physicsguard.module_semantics.source_first_compiler.v1"
SOURCE_IR_SCHEMA = ledger_checker.SOURCE_SEMANTIC_IR_SCHEMA

GOLD_MODULES = frozenset(runtime_ports.INTRINSIC_ROLE_AUTHORITY_RESOURCES)
SCENARIO_ROLE_MODULES = runtime_ports.BOUNDARY_DERIVED_ROLE_MODULES
MECHANICAL_DRAFT_MODULES = frozenset(
    runtime_ports.MECHANICAL_DRAFT_ROLE_AUTHORITY_RESOURCES
)
SOURCE_FIRST_MODULES = frozenset(
    runtime_ports.SOURCE_FIRST_ROLE_AUTHORITY_RESOURCES
)
FORMULA_MODULES = frozenset(
    SCENARIO_ROLE_MODULES | MECHANICAL_DRAFT_MODULES | SOURCE_FIRST_MODULES
)
COMPILED_MODULES = frozenset(GOLD_MODULES | FORMULA_MODULES)
SCENARIO_FORMULA_SCHEMA = "physicsguard.project_formula.v1"
SCENARIO_FORMULA_RESOURCES = {
    module_type: f".physicsguard/module_formulas/{module_type}.yaml"
    for module_type in FORMULA_MODULES
}
UNIT_CONVENTION_IDENTITY = "physicsguard.project.si.v1"
CANONICAL_DIMENSION_UNITS = {
    "area": "m^2",
    "acceleration": "m/s^2",
    "angular_acceleration": "rad/s^2",
    "angular_velocity": "rad/s",
    "damping": "N*s/m",
    "duration": "s",
    "count": "count",
    "current_density": "A/m^2",
    "density": "kg/m^3",
    "dimensionless": "1",
    "boolean": "boolean",
    "enum": "enum",
    "displacement": "m",
    "electric_current": "A",
    "force": "N",
    "mass": "kg",
    "mass_flow": "kg/s",
    "moment_of_inertia": "kg*m^2",
    "molar_flow": "mol/s",
    "molar_mass": "kg/mol",
    "mole_fraction": "1",
    "power": "W",
    "pressure": "Pa",
    "reciprocal_time": "1/s",
    "specific_energy": "J/kg",
    "specific_heat": "J/(kg*K)",
    "specific_stiffness": "N/m",
    "temperature": "K",
    "velocity": "m/s",
    "voltage": "V",
    "volume": "m^3",
    "volume_flow": "m^3/s",
    "torque": "N*m",
    "irradiance": "W/m^2",
    "conductance": "W/K",
    "heat_capacity": "J/K",
    "heat_transfer_coefficient": "W/(m^2*K)",
    "length": "m",
    "resistance": "Ohm",
    "squared_mass_flow": "kg^2/s^2",
    "temperature_rate": "K/s",
}
REQUIRED_EVALUATION_PREDICATES = {
    "AggregateEfficiencyModule": {"abs(input_power) >= denominator_min_abs"},
    "EfficiencyModule": {"abs(input_power_W) >= denominator_min_abs"},
    "IdealGasDensityModule": {"abs(T_K) >= temperature_min_abs"},
    "PressureRatioModule": {"abs(p_in_Pa) >= denominator_min_abs"},
    "RatioModule": {"abs(denominator) >= denominator_min_abs"},
    "StackChemicalEfficiencyModule": {"abs(P_chemical_W) >= denominator_min_abs"},
}

# The compiler is intentionally narrow.  These are source-observed or
# independently role-authorized projections; domain meaning remains author
# owned and cannot be filled by this program.
COMPILER_OWNED_PATH_PREFIXES = (
    "source_semantic_ir",
    "purpose",
    "function_block.configuration",
    "function_block.declared_variables",
    "function_block.external_inputs",
    "function_block.state.previous",
    "function_block.state.current",
    "function_block.state.next",
    "function_block.outputs.declared_variables",
    "function_block.role_authority",
    "function_block.preconditions",
    "function_block.effects",
    "function_block.postconditions",
    "function_block.termination",
    "function_block.failures",
    "behavior_contract",
    "residual_definitions",
    "symbol_units",
    "unit_convention",
    "constraints",
    "regions",
    "assumptions",
    "invariants",
    "bindings.resources",
    "bindings.oracle",
    "bindings.behavioral_tests",
    "bindings.instantiation.selector",
    "provenance",
    "stale_triggers",
    "semantic_review.subject_fingerprint",
)
PRESERVED_DOMAIN_PATHS = (
    "residual_program",
    "diagnostic_keys",
    "semantic_review.status",
    "semantic_review.license",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _mapping_list(value: Any, label: str, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or not all(isinstance(item, dict) for item in value)
    ):
        suffix = " (empty allowed)" if allow_empty else ""
        raise ValueError(f"{label} must be a list of mappings{suffix}")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or not all(isinstance(item, str) and item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        suffix = " (empty allowed)" if allow_empty else ""
        raise ValueError(f"{label} must be a unique string list{suffix}")
    return value


def _normalize_formula_scalars(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_formula_scalars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_formula_scalars(item) for item in value]
    if isinstance(value, str) and re.fullmatch(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)[eE][-+]?\d+", value
    ):
        return float(value)
    return value


def _validate_dimension_unit(dimension: Any, unit: Any, label: str) -> tuple[str, str]:
    dimension_value = _string(dimension, f"{label}.dimension")
    unit_value = _string(unit, f"{label}.unit")
    expected = CANONICAL_DIMENSION_UNITS.get(dimension_value)
    if expected is None:
        raise ValueError(f"{label}: dimension {dimension_value!r} has no current SI derivation")
    if unit_value != expected:
        raise ValueError(
            f"{label}: unit {unit_value!r} does not derive from dimension "
            f"{dimension_value!r}; expected {expected!r}"
        )
    return dimension_value, unit_value


def _constructor_parameter_semantics(
    record: dict[str, Any],
    module_type: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if module_type not in SOURCE_FIRST_MODULES:
        return _legacy_constructor_parameter_semantics(record, module_type)

    bindings = record.get("bindings")
    implementation = (
        bindings.get("implementation")
        if isinstance(bindings, dict) and isinstance(bindings.get("implementation"), dict)
        else {}
    )
    resolved = ledger_checker._resolve_python_symbol(
        module_type, implementation.get("python_symbol")
    )
    if resolved.get("error") or not inspect.isclass(resolved.get("value")):
        raise ValueError(
            f"{module_type}: maintained implementation class is unavailable: "
            f"{resolved.get('error') or 'not a class'}"
        )
    implementation_class = resolved["value"]
    semantics: dict[str, dict[str, Any]] = {}

    # Read every maintained constructor in the MRO.  A derived constructor is
    # the current owner when it mentions the same parameter again.  This avoids
    # silently dropping equation/configuration parameters that are validated by
    # a base constructor or by a helper wrapped around ``parameters.get``.
    constructors: list[tuple[type[Any], ast.AST]] = []
    for owner in reversed(implementation_class.__mro__):
        if not getattr(owner, "__module__", "").startswith("physicsguard."):
            continue
        initializer = owner.__dict__.get("__init__")
        if initializer is None:
            continue
        try:
            source = textwrap.dedent(inspect.getsource(initializer))
            constructors.append((owner, ast.parse(source)))
        except (OSError, TypeError, SyntaxError) as exc:
            raise ValueError(
                f"{module_type}: constructor parameter source is unavailable for "
                f"{owner.__module__}.{owner.__qualname__}: {exc}"
            ) from exc

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    for owner, tree in constructors:
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        candidates: dict[str, list[dict[str, Any]]] = {}
        for node in ast.walk(tree):
            name: str | None = None
            required: bool | None = None
            default: Any = None
            guard_node: ast.AST = node
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "parameters"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                name = node.slice.value
                required = True
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "parameters"
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                name = node.args[0].value
                parent = parents.get(node)
                parent_call = parent if isinstance(parent, ast.Call) else None
                parent_helper = call_name(parent_call.func) if parent_call else None
                if len(node.args) > 1:
                    try:
                        default = ast.literal_eval(node.args[1])
                    except (ValueError, TypeError):
                        continue
                    required = False
                else:
                    required = not (
                        isinstance(parent_helper, str)
                        and "optional" in parent_helper.lower()
                    )
                    default = None
                if parent_call is not None:
                    guard_node = parent_call
            elif (
                isinstance(node, ast.Call)
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "parameters"
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                helper = call_name(node.func) or ""
                name = node.args[1].value
                required_keyword = next(
                    (
                        item.value.value
                        for item in node.keywords
                        if item.arg == "required"
                        and isinstance(item.value, ast.Constant)
                        and isinstance(item.value.value, bool)
                    ),
                    None,
                )
                if required_keyword is not None:
                    required = required_keyword
                else:
                    required = "optional" not in helper.lower()
                default = None if required else []
            if name is None or required is None:
                continue
            candidate = {
                "required": required,
                "default": copy.deepcopy(default),
                "source_expression": ast.unparse(node),
                "guard_expression": ast.unparse(guard_node),
                "definition_owner": f"{owner.__module__}.{owner.__qualname__}",
            }
            candidates.setdefault(name, []).append(candidate)

        for name, items in candidates.items():
            # Prefer the access that carries an explicit literal default; when
            # all accesses are required, retain the most specific guard call.
            selected = next(
                (item for item in items if item["required"] is False),
                items[0],
            )
            conflicts = {
                (item["required"], json.dumps(item["default"], sort_keys=True))
                for item in items
            }
            if len(conflicts) > 1:
                required_items = [item for item in items if item["required"]]
                optional_items = [item for item in items if not item["required"]]
                # A validating wrapper around a get-with-default is optional;
                # the explicit default remains authoritative.  All other
                # disagreements are ambiguous and block compilation.
                if not optional_items or not required_items:
                    raise ValueError(
                        f"{module_type}.{name}: constructor parameter semantics conflict"
                    )
                selected = optional_items[0]
            semantics[name] = selected

    # Constructors frequently delegate variable-bound and domain-parameter
    # parsing to maintained helpers.  The terminal ``__init__`` AST alone is
    # therefore not a complete configuration denominator (for example,
    # ``power_record(..., parameters, ..., initial)`` and ``self._record``
    # consume additional bound/guess/scale keys).  Follow only resolvable
    # project-local pure Python callables, bind literal key/default arguments,
    # and collect their concrete parameter accesses.  This remains static and
    # source-grounded: no constructor is executed and no guessed key is added.
    _PARAMETER_MAP = object()
    recursive_candidates: dict[str, list[dict[str, Any]]] = {}
    active_calls: set[tuple[str, str]] = set()
    exact_parameters = (
        record.get("bindings", {})
        .get("instantiation", {})
        .get("parameters", {})
    )

    def literal_value(node: ast.AST, values: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return copy.deepcopy(node.value)
        if isinstance(node, ast.Name) and node.id in values:
            return copy.deepcopy(values[node.id])
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and node.attr in exact_parameters
        ):
            return copy.deepcopy(exact_parameters[node.attr])
        if isinstance(node, (ast.List, ast.Tuple)):
            return [literal_value(item, values) for item in node.elts]
        if isinstance(node, ast.Dict):
            return {
                literal_value(key, values): literal_value(value, values)
                for key, value in zip(node.keys, node.values, strict=True)
                if key is not None
            }
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = literal_value(node.operand, values)
            if not isinstance(operand, (int, float)) or isinstance(operand, bool):
                raise ValueError("non-numeric unary literal")
            return +operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left = literal_value(node.left, values)
            right = literal_value(node.right, values)
            if (
                not isinstance(left, (int, float))
                or isinstance(left, bool)
                or not isinstance(right, (int, float))
                or isinstance(right, bool)
            ):
                raise ValueError("non-numeric bound expression")
            operations = {
                ast.Add: lambda: left + right,
                ast.Sub: lambda: left - right,
                ast.Mult: lambda: left * right,
                ast.Div: lambda: left / right,
                ast.Pow: lambda: left**right,
            }
            operation = operations.get(type(node.op))
            if operation is None:
                raise ValueError("unsupported bound arithmetic")
            return operation()
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for item in node.values:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    parts.append(item.value)
                elif isinstance(item, ast.FormattedValue):
                    parts.append(str(literal_value(item.value, values)))
                else:
                    raise ValueError("dynamic formatted literal")
            return "".join(parts)
        raise ValueError("expression is not a bound literal")

    def parameter_map_expression(node: ast.AST, map_names: set[str]) -> bool:
        return (
            isinstance(node, ast.Name)
            and node.id in map_names
        ) or (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and node.attr == "parameters"
        )

    def rendered_expression(node: ast.AST, values: dict[str, Any]) -> str:
        class _BoundLiteralSubstitution(ast.NodeTransformer):
            def visit_Name(self, current: ast.Name) -> ast.AST:  # noqa: N802
                if current.id not in values:
                    return current
                return ast.copy_location(
                    ast.Constant(value=copy.deepcopy(values[current.id])), current
                )

        projected = _BoundLiteralSubstitution().visit(copy.deepcopy(node))
        ast.fix_missing_locations(projected)
        return ast.unparse(projected)

    def optional_annotation(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
        current = parents.get(node)
        while current is not None and not isinstance(current, (ast.Assign, ast.AnnAssign)):
            if isinstance(current, (ast.Call, ast.IfExp, ast.BinOp, ast.Compare)):
                return False
            current = parents.get(current)
        if not isinstance(current, ast.AnnAssign):
            return False
        return "Optional" in ast.unparse(current.annotation) or "None" in ast.unparse(
            current.annotation
        )

    def add_recursive_candidate(
        *,
        name: str,
        required: bool,
        default: Any,
        source_expression: str,
        guard_expression: str,
        definition_owner: str,
        priority: int,
    ) -> None:
        if not isinstance(name, str) or not name:
            return
        recursive_candidates.setdefault(name, []).append(
            {
                "required": required,
                "default": copy.deepcopy(default),
                "source_expression": source_expression,
                "guard_expression": guard_expression,
                "definition_owner": definition_owner,
                "priority": priority,
            }
        )

    def resolved_target(
        node: ast.Call,
        namespace: dict[str, Any],
        owner_class: type[Any],
    ) -> tuple[Any, bool]:
        if isinstance(node.func, ast.Name):
            return namespace.get(node.func.id), False
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
        ):
            return getattr(owner_class, node.func.attr, None), True
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            base = namespace.get(node.func.value.id)
            return getattr(base, node.func.attr, None), False
        return None, False

    def collect_callable(
        current: Any,
        *,
        owner_class: type[Any],
        values: dict[str, Any],
        map_names: set[str],
        depth: int,
    ) -> None:
        if depth > 12 or not (inspect.isfunction(current) or inspect.ismethod(current)):
            return
        identity = f"{getattr(current, '__module__', '')}.{getattr(current, '__qualname__', repr(current))}"
        if not identity.startswith("physicsguard."):
            return
        call_key = (identity, json.dumps(values, sort_keys=True, default=repr))
        if call_key in active_calls:
            return
        active_calls.add(call_key)
        try:
            source = textwrap.dedent(inspect.getsource(current))
            tree = ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            active_calls.remove(call_key)
            return
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        namespace = getattr(current, "__globals__", {})

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Subscript)
                and parameter_map_expression(node.value, map_names)
            ):
                try:
                    name = literal_value(node.slice, values)
                except ValueError:
                    continue
                if isinstance(name, str):
                    add_recursive_candidate(
                        name=name,
                        required=True,
                        default=None,
                        source_expression=rendered_expression(node, values),
                        guard_expression=rendered_expression(
                            parents.get(node, node), values
                        ),
                        definition_owner=identity,
                        priority=30 + depth,
                    )
            if not isinstance(node, ast.Call):
                continue

            # Direct mapping.get(key, default) accesses.
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and parameter_map_expression(node.func.value, map_names)
                and node.args
            ):
                try:
                    name = literal_value(node.args[0], values)
                except ValueError:
                    name = None
                if isinstance(name, str):
                    parent_call = parents.get(node)
                    helper_name = (
                        call_name(parent_call.func)
                        if isinstance(parent_call, ast.Call)
                        else None
                    ) or ""
                    if len(node.args) > 1:
                        try:
                            default = literal_value(node.args[1], values)
                        except ValueError:
                            default = None
                        required = False
                    elif optional_annotation(node, parents) or "optional" in helper_name.lower():
                        default = None
                        required = False
                    else:
                        default = None
                        required = bool(helper_name)
                    add_recursive_candidate(
                        name=name,
                        required=required,
                        default=default,
                        source_expression=rendered_expression(node, values),
                        guard_expression=rendered_expression(
                            parent_call if isinstance(parent_call, ast.Call) else node,
                            values,
                        ),
                        definition_owner=identity,
                        priority=50 + depth,
                    )

            target, implicit_self = resolved_target(node, namespace, owner_class)
            if not (inspect.isfunction(target) or inspect.ismethod(target)):
                continue
            try:
                signature = inspect.signature(target)
            except (TypeError, ValueError):
                continue
            formal_names = list(signature.parameters)
            bound_values: dict[str, Any] = {}
            bound_maps: set[str] = set()
            positional_offset = 1 if implicit_self and formal_names and formal_names[0] in {"self", "cls"} else 0
            for formal, argument in zip(formal_names[positional_offset:], node.args, strict=False):
                if parameter_map_expression(argument, map_names):
                    bound_maps.add(formal)
                    continue
                try:
                    bound_values[formal] = literal_value(argument, values)
                except ValueError:
                    pass
            for keyword in node.keywords:
                if keyword.arg is None:
                    continue
                if parameter_map_expression(keyword.value, map_names):
                    bound_maps.add(keyword.arg)
                    continue
                try:
                    bound_values[keyword.arg] = literal_value(keyword.value, values)
                except ValueError:
                    pass
            for formal, parameter in signature.parameters.items():
                if formal in bound_values or formal in bound_maps:
                    continue
                if parameter.default is not inspect.Parameter.empty:
                    bound_values[formal] = copy.deepcopy(parameter.default)

            # A maintained helper with an explicit map + literal key is useful
            # provenance even when its body is a native/opaque validator.
            if bound_maps:
                key = next(
                    (
                        value
                        for formal, value in bound_values.items()
                        if isinstance(value, str)
                        and formal in {"name", "key", "parameter", "parameter_name"}
                    ),
                    None,
                )
                if key is None and len(node.args) >= 2:
                    try:
                        projected = literal_value(node.args[1], values)
                        key = projected if isinstance(projected, str) else None
                    except ValueError:
                        key = None
                if isinstance(key, str):
                    required_flag = bound_values.get("required")
                    target_name = getattr(target, "__name__", "")
                    required = (
                        bool(required_flag)
                        if isinstance(required_flag, bool)
                        else "optional" not in target_name.lower()
                    )
                    default = None if required else [] if "list" in target_name.lower() else None
                    parent = parents.get(node)
                    if isinstance(parent, ast.IfExp):
                        other = parent.orelse if parent.body is node else parent.body
                        try:
                            if isinstance(other, ast.Call) and other.args:
                                default = literal_value(other.args[0], values)
                            else:
                                default = literal_value(other, values)
                            required = False
                        except ValueError:
                            pass
                    add_recursive_candidate(
                        name=key,
                        required=required,
                        default=default,
                        source_expression=rendered_expression(node, values),
                        guard_expression=rendered_expression(node, values),
                        definition_owner=identity,
                        priority=70 + depth,
                    )

            collect_callable(
                target,
                owner_class=owner_class,
                values=bound_values,
                map_names=bound_maps,
                depth=depth + 1,
            )
        active_calls.remove(call_key)

    for owner in reversed(implementation_class.__mro__):
        if not getattr(owner, "__module__", "").startswith("physicsguard."):
            continue
        initializer = owner.__dict__.get("__init__")
        if initializer is not None:
            collect_callable(
                initializer,
                owner_class=implementation_class,
                values={},
                map_names={"parameters"},
                depth=0,
            )

    for name, items in recursive_candidates.items():
        # Prefer a concrete optional default over a required access used by a
        # conditional branch; otherwise retain the closest/highest-priority
        # maintained source guard.
        selected = max(
            items,
            key=lambda item: (
                item["required"] is False,
                item["default"] is not None,
                item["priority"],
            ),
        )
        current = semantics.get(name)
        if current is None or (
            selected["required"] is False and current["required"] is True
        ):
            selected = {key: value for key, value in selected.items() if key != "priority"}
            semantics[name] = selected
    if not semantics:
        raise ValueError(f"{module_type}: no constructor parameter provenance was derived")
    return semantics, copy.deepcopy(implementation)


def _legacy_constructor_parameter_semantics(
    record: dict[str, Any],
    module_type: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Keep the pre-existing compiler projection byte-stable outside task 8.15."""

    bindings = record.get("bindings")
    implementation = (
        bindings.get("implementation")
        if isinstance(bindings, dict) and isinstance(bindings.get("implementation"), dict)
        else {}
    )
    resolved = ledger_checker._resolve_python_symbol(
        module_type, implementation.get("python_symbol")
    )
    if resolved.get("error") or not inspect.isclass(resolved.get("value")):
        raise ValueError(
            f"{module_type}: maintained implementation class is unavailable: "
            f"{resolved.get('error') or 'not a class'}"
        )
    implementation_class = resolved["value"]
    try:
        source = textwrap.dedent(inspect.getsource(implementation_class.__init__))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError) as exc:
        raise ValueError(
            f"{module_type}: constructor parameter source is unavailable: {exc}"
        ) from exc

    semantics: dict[str, dict[str, Any]] = {}
    required_helpers = {
        "required",
        "required_positive",
        "_required",
        "_required_parameter",
        "_required_positive",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name: str | None = None
        required: bool | None = None
        default: Any = None
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "parameters"
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            name = node.args[0].value
            required = False
            try:
                default = ast.literal_eval(node.args[1]) if len(node.args) > 1 else None
            except (ValueError, TypeError):
                continue
        elif (
            isinstance(node.func, ast.Name)
            and node.func.id in required_helpers
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "parameters"
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            name = node.args[1].value
            required = True
            default = None
        if name is None or required is None:
            continue
        observed = {
            "required": required,
            "default": default,
            "source_expression": ast.unparse(node),
        }
        prior = semantics.get(name)
        if prior is not None and (
            prior["required"] != observed["required"]
            or prior["default"] != observed["default"]
        ):
            raise ValueError(
                f"{module_type}.{name}: constructor parameter semantics conflict"
            )
        semantics[name] = observed
    if not semantics:
        raise ValueError(f"{module_type}: no constructor parameter provenance was derived")
    return semantics, copy.deepcopy(implementation)


def _load_scenario_formula(root: Path, module_type: str) -> tuple[dict[str, Any], str, str]:
    relative_path = SCENARIO_FORMULA_RESOURCES[module_type]
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{module_type}: formula authority escapes the repository") from exc
    if not path.is_file():
        raise ValueError(f"{module_type}: formula authority is missing: {relative_path}")
    payload = _normalize_formula_scalars(
        yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    )
    if not isinstance(payload, dict):
        raise ValueError(f"{module_type}: formula authority must be a mapping")
    if payload.get("schema") != SCENARIO_FORMULA_SCHEMA or payload.get("module_type") != module_type:
        raise ValueError(f"{module_type}: formula authority identity is stale")
    _string(payload.get("owner"), f"{module_type}.owner")
    _string(payload.get("purpose"), f"{module_type}.purpose")
    _string(payload.get("claim_boundary"), f"{module_type}.claim_boundary")
    if module_type in MECHANICAL_DRAFT_MODULES:
        if (
            payload.get("authoring_status")
            != "mechanical_draft_pending_independent_review"
            or payload.get("separate_review_status") != "pending"
            or payload.get("physical_claim_licensed") is not False
            or payload.get("direction_scope")
            != "exact_instantiation_mechanical_draft"
        ):
            raise ValueError(
                f"{module_type}: formula must remain an explicit unlicensed mechanical draft"
            )
    elif module_type in SOURCE_FIRST_MODULES:
        if (
            payload.get("authoring_status")
            != "source_first_reconstruction_pending_independent_review"
            or payload.get("separate_review_status") != "pending"
            or payload.get("physical_claim_licensed") is not False
            or payload.get("direction_scope")
            != "exact_instantiation_source_first_reconstruction"
        ):
            raise ValueError(
                f"{module_type}: formula must remain an explicit unlicensed "
                "source-first reconstruction"
            )
    elif payload.get("direction_scope") != "exact_instantiation_scenario":
        raise ValueError(f"{module_type}: formula must preserve exact scenario direction scope")
    if payload.get("relation_directionality") != "direction_neutral":
        raise ValueError(f"{module_type}: formula cannot promote the relation to a fixed direction")
    return payload, relative_path.replace("\\", "/"), _sha256(path)


def _project_unit_convention(root: Path) -> dict[str, Any]:
    path = root / ledger_checker.UNIT_CONVENTION_REGISTRY_PATH
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    conventions = payload.get("conventions") if isinstance(payload, dict) else None
    matches = [
        item
        for item in conventions or []
        if isinstance(item, dict) and item.get("identity") == UNIT_CONVENTION_IDENTITY
    ]
    if len(matches) != 1:
        raise ValueError("the exact current SI unit convention is unavailable")
    return copy.deepcopy(matches[0])


def _formula_ports(
    formula: dict[str, Any],
    module_type: str,
    runtime_entry: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs = _mapping_list(
        formula.get("scenario_inputs"),
        f"{module_type}.scenario_inputs",
        allow_empty=module_type in SOURCE_FIRST_MODULES,
    )
    outputs = _mapping_list(
        formula.get("scenario_outputs"),
        f"{module_type}.scenario_outputs",
        allow_empty=module_type in (MECHANICAL_DRAFT_MODULES | SOURCE_FIRST_MODULES),
    )
    formula_ports: dict[str, tuple[str, str, str]] = {}
    allowed_roles = {"input", "output", "state_previous", "state_current", "state_next"}
    for default_direction, items in (("input", inputs), ("output", outputs)):
        for item in items:
            name = _string(item.get("name"), f"{module_type}.{default_direction}.name")
            dimension, unit = _validate_dimension_unit(
                item.get("dimension"), item.get("unit"), f"{module_type}.{name}"
            )
            direction = item.get("role", default_direction)
            if direction not in allowed_roles:
                raise ValueError(f"{module_type}.{name}: formula port role is invalid")
            if name in formula_ports:
                raise ValueError(f"{module_type}: formula duplicates port {name}")
            formula_ports[name] = (str(direction), unit, dimension)
    declared_units = {
        str(item["name"]): str(item.get("unit"))
        for item in runtime_entry.get("declared_ports", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    runtime_directions = {
        str(item["name"]): str(item.get("direction"))
        for item in runtime_entry.get("ports", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    external_units = {
        str(item["name"]): str(item.get("unit"))
        for item in runtime_entry.get("external_ports", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    runtime_ports_by_name = {
        name: (runtime_directions[name], declared_units[name])
        for name in set(declared_units) & set(runtime_directions)
    }
    runtime_ports_by_name.update(
        {
            name: (runtime_directions[name], external_units[name])
            for name in set(external_units) & set(runtime_directions)
        }
    )
    if set(formula_ports) != set(runtime_ports_by_name):
        raise ValueError(f"{module_type}: formula does not exactly cover the current scenario ports")
    mismatches = sorted(
        name
        for name, (direction, unit, _) in formula_ports.items()
        if runtime_ports_by_name[name] != (direction, unit)
    )
    if mismatches:
        raise ValueError(f"{module_type}: formula scenario port direction/unit is stale: {mismatches}")
    return inputs, outputs


def _formula_configuration(
    formula: dict[str, Any],
    module_type: str,
    source_semantics: dict[str, dict[str, Any]],
    implementation: dict[str, Any],
) -> list[dict[str, Any]]:
    configuration = _mapping_list(
        formula.get("configuration"), f"{module_type}.configuration", allow_empty=True
    )
    names: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in configuration:
        name = _string(item.get("name"), f"{module_type}.configuration.name")
        if name in names:
            raise ValueError(f"{module_type}: formula duplicates configuration {name}")
        names.add(name)
        if not isinstance(item.get("required"), bool) or "default" not in item:
            raise ValueError(f"{module_type}.{name}: required/default must be explicit")
        _, unit = _validate_dimension_unit(
            item.get("dimension"), item.get("unit"), f"{module_type}.{name}"
        )
        constraints = _string_list(
            item.get("constraints", []), f"{module_type}.{name}.constraints", allow_empty=True
        )
        observed = source_semantics.get(name)
        if observed is None:
            raise ValueError(
                f"{module_type}.{name}: formula parameter has no maintained-source provenance"
            )
        if (
            item["required"] != observed["required"]
            or item["default"] != observed["default"]
        ):
            raise ValueError(
                f"{module_type}.{name}: required/default semantics disagree with maintained source"
            )
        parameter_provenance = {
            "implementation_path": implementation.get("path"),
            "implementation_selector": implementation.get("selector"),
            "source_expression": observed["source_expression"],
        }
        if module_type in SOURCE_FIRST_MODULES:
            parameter_provenance.update(
                {
                    "guard_expression": observed["guard_expression"],
                    "definition_owner": observed["definition_owner"],
                }
            )
        result.append(
            {
                "name": name,
                "required": item["required"],
                "default": copy.deepcopy(item["default"]),
                "unit": unit,
                "constraints": constraints,
                "parameter_provenance": parameter_provenance,
            }
        )
    if module_type in SOURCE_FIRST_MODULES and names != set(source_semantics):
        missing = sorted(set(source_semantics) - names)
        extra = sorted(names - set(source_semantics))
        raise ValueError(
            f"{module_type}: source-first formula configuration is incomplete; "
            f"missing={missing}, extra={extra}"
        )
    return result


def _compile_formula_constraints(
    formula: dict[str, Any],
    module_type: str,
    source_fingerprint: str,
) -> dict[str, list[dict[str, Any]]]:
    declared = formula.get("constraints")
    if not isinstance(declared, dict):
        raise ValueError(f"{module_type}: formula constraints must be a mapping")
    result: dict[str, list[dict[str, Any]]] = {"constructor": [], "evaluation": []}
    for group in result:
        for item in _mapping_list(
            declared.get(group), f"{module_type}.constraints.{group}", allow_empty=True
        ):
            predicate = _string(item.get("predicate"), f"{module_type}.{group}.predicate")
            dependencies = sorted(
                ledger_checker._expression_identifiers(predicate)
                - ledger_checker.EXPRESSION_BUILTINS
            )
            if not dependencies:
                raise ValueError(f"{module_type}: constraint predicate has no dependencies")
            cases = _mapping_list(item.get("cases"), f"{module_type}.{group}.cases")
            result[group].append(
                {
                    "predicate": predicate,
                    "dependencies": dependencies,
                    "on_violation": _string(
                        item.get("on_violation"), f"{module_type}.{group}.on_violation"
                    ),
                    "implementation_binding": {
                        "source_semantic_ir_fingerprint": source_fingerprint,
                        "guard_signature": _string(
                            item.get("guard_signature"), f"{module_type}.{group}.guard_signature"
                        ),
                        "failure_type": _string(
                            item.get("failure_type"), f"{module_type}.{group}.failure_type"
                        ),
                        "message_selector": _string(
                            item.get("message_selector"), f"{module_type}.{group}.message_selector"
                        ),
                    },
                    "cases": copy.deepcopy(cases),
                }
            )
    if not any(result.values()):
        raise ValueError(f"{module_type}: formula must declare at least one executable constraint")
    evaluation_predicates = {item["predicate"] for item in result["evaluation"]}
    missing_evaluation = REQUIRED_EVALUATION_PREDICATES.get(module_type, set()) - evaluation_predicates
    if missing_evaluation:
        raise ValueError(
            f"{module_type}: protected denominator evaluation predicate is missing: "
            f"{sorted(missing_evaluation)}"
        )
    return result


def _compile_formula_regions(formula: dict[str, Any], module_type: str) -> dict[str, list[dict[str, Any]]]:
    declared = formula.get("regions")
    if not isinstance(declared, dict):
        raise ValueError(f"{module_type}: formula regions must be a mapping")
    result: dict[str, list[dict[str, Any]]] = {}
    for group in ("valid", "invalid"):
        result[group] = []
        for item in _mapping_list(declared.get(group), f"{module_type}.regions.{group}"):
            predicate = _string(item.get("predicate"), f"{module_type}.{group}.predicate")
            result[group].append(
                {
                    "predicate": predicate,
                    "dependencies": sorted(
                        ledger_checker._expression_identifiers(predicate)
                        - ledger_checker.EXPRESSION_BUILTINS
                    ),
                    "meaning": _string(item.get("meaning"), f"{module_type}.{group}.meaning"),
                    "cases": copy.deepcopy(
                        _mapping_list(item.get("cases"), f"{module_type}.{group}.cases")
                    ),
                }
            )
    return result


def _complete_source_branch_projection(
    residual: dict[str, Any], source_contract: dict[str, Any]
) -> None:
    """Keep both normalized sides of every residual-affecting source branch.

    The recursive source reader owns the branch identities.  A formula draft
    may express the same piecewise relation more compactly, so retain its
    existing branch expressions and add only the missing normalized side with
    the complete residual expression as the branch result.
    """

    branches = residual.get("branches")
    if not isinstance(branches, list):
        return
    closure = ledger_checker._residual_symbol_closure(residual)
    branches[:] = [
        item
        for item in branches
        if isinstance(item, dict)
        and not (
            (
                ledger_checker._expression_identifiers(
                    str(item.get("condition", ""))
                )
                | ledger_checker._expression_identifiers(
                    str(item.get("expression", ""))
                )
            )
            - ledger_checker.EXPRESSION_BUILTINS
            - closure
        )
    ]
    if not branches:
        residual["piecewise"] = False
    signatures = {
        ledger_checker._expression_signature(item.get("condition"))
        for item in branches
        if isinstance(item, dict)
    }
    for condition in source_contract.get("conditions", []):
        if not isinstance(condition, dict):
            continue
        affected = {
            str(item)
            for item in condition.get("affected_symbols", [])
            if isinstance(item, str)
        }
        if not affected or not (affected & closure):
            continue
        display = condition.get("condition")
        if not isinstance(display, str):
            continue
        if (
            ledger_checker._expression_identifiers(display)
            - ledger_checker.EXPRESSION_BUILTINS
            - closure
        ):
            continue
        try:
            positive_node = ledger_checker._normalized_source_node(
                ast.parse(display, mode="eval").body, {}
            )
        except (SyntaxError, ValueError):
            continue
        projected_nodes = (
            positive_node,
            ledger_checker._normalized_source_node(
                ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(positive_node)),
                {},
            ),
        )
        for node in projected_nodes:
            projected_condition = ast.unparse(node)
            signature = ledger_checker._expression_signature(projected_condition)
            if signature in signatures:
                continue
            branches.append(
                {
                    "condition": projected_condition,
                    "expression": str(residual["expression"]),
                }
            )
            signatures.add(signature)


def _normalize_implementation_projection_expression(
    expression: str,
    attribute_parameters: dict[str, str],
) -> str:
    """Project maintained Python aliases onto public configuration names."""

    try:
        parsed = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return expression

    class _PublicParameterProjection(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
            replacement = attribute_parameters.get(node.id)
            if replacement is None:
                return node
            return ast.copy_location(ast.Name(id=replacement, ctx=node.ctx), node)

    normalized = ledger_checker._normalized_source_node(parsed, {})
    normalized = _PublicParameterProjection().visit(normalized)
    ast.fix_missing_locations(normalized)
    return ast.unparse(normalized)


def _mechanical_behavior_bindings(
    root: Path,
    record: dict[str, Any],
    formula: dict[str, Any],
    module_type: str,
    source_contract: dict[str, Any],
    *,
    test_path: str = "tests/test_module_semantics_batch_mechanically_draftable_02.py",
    positive_selector: str = "test_mechanical_draft_oracle_matches_current_runtime",
    counterexample_selector: str = (
        "test_mechanical_draft_constructor_counterexample_still_fails"
    ),
    obligation_label: str = "bounded mechanical-draft",
) -> dict[str, Any]:
    test_sha256 = _sha256(root / test_path)
    component_id = str(record["bindings"]["instantiation"]["component_id"])
    first_case = _mapping_list(
        formula.get("oracle_cases"), f"{module_type}.oracle_cases"
    )[0]
    case_inputs = copy.deepcopy(first_case["inputs"])
    configuration_names = {
        str(item["name"])
        for item in formula["configuration"]
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    parameters = copy.deepcopy(record["bindings"]["instantiation"]["parameters"])
    parameters.update(
        {
            name: value
            for name, value in case_inputs.items()
            if name in configuration_names
        }
    )
    values: dict[str, Any] = {}
    external_variables: list[dict[str, str]] = []
    for port in [*formula["scenario_inputs"], *formula["scenario_outputs"]]:
        name = str(port["name"])
        if port.get("source_kind") == "external":
            reference = str(port["source_reference"])
            values[reference] = case_inputs[name]
            external_variables.append(
                {"name": reference, "unit": str(port["unit"])}
            )
        else:
            values[f"{component_id}.{name}"] = case_inputs[name]

    residual_formula = formula["residuals"][0]
    residual_definition_name = str(residual_formula["name"])
    residual_name = str(
        residual_formula.get("runtime_name", residual_definition_name)
    )
    residual_record = next(
        item
        for item in record["residual_definitions"]
        if item["name"] == residual_definition_name
    )
    source_role = source_contract.get("roles", {}).get(residual_definition_name)
    observed_role = (
        source_role
        if source_role in {"equation", "soft_check", "post_check"}
        else case_inputs["role"]
    )
    positive_outcome = {
        "kind": "residual_record",
        "residual_fields": list(ledger_checker.EXPECTED_RESIDUAL_FIELDS),
    }
    positive_contract = {
        "runner_identity": ledger_checker.CASE_RUNNER_IDENTITY,
        "inputs": {
            "component_id": component_id,
            "parameters": parameters,
            "variables": values,
            "external_variables": sorted(
                external_variables, key=lambda item: item["name"]
            ),
        },
        "obligation": (
            f"{module_type} reproduces the {obligation_label} oracle case "
            "without licensing its physical meaning"
        ),
        "assertion_kind": "residual_record",
        "expected_fingerprint": ledger_checker._canonical_hash(positive_outcome),
        "expected_observation": {
            "name": residual_name,
            "value": first_case["expected"][residual_definition_name],
            "role": observed_role,
            "scale": ledger_checker._restricted_expression(
                str(residual_formula["scale_expression"]), case_inputs
            ),
            "diagnostic_key": residual_record["diagnostic_key"],
        },
        "tolerance": first_case["tolerance"],
    }

    constructor_constraints = _mapping_list(
        formula["constraints"].get("constructor"),
        f"{module_type}.constraints.constructor",
    )
    protected_constraint = next(
        item
        for item in constructor_constraints
        if any(
            case.get("kind") == "outside"
            for case in item.get("cases", [])
            if isinstance(case, dict)
        )
    )
    outside_case = next(
        case
        for case in protected_constraint["cases"]
        if case.get("kind") == "outside"
    )
    bad_parameters = copy.deepcopy(record["bindings"]["instantiation"]["parameters"])
    bad_parameters.update(
        {
            name: value
            for name, value in outside_case["inputs"].items()
            if name in configuration_names
        }
    )
    counter_outcome = {
        "kind": "raises",
        "exception_type": protected_constraint["failure_type"],
        "message_selector": protected_constraint["message_selector"],
    }
    counter_contract = {
        "runner_identity": ledger_checker.CASE_RUNNER_IDENTITY,
        "inputs": {
            "component_id": component_id,
            "parameters": bad_parameters,
            "variables": {},
            "external_variables": [],
        },
        "obligation": f"{module_type} rejects its bounded protected constructor case",
        "assertion_kind": "raises",
        "expected_fingerprint": ledger_checker._canonical_hash(counter_outcome),
    }
    return {
        "positive": {
            "disposition": "bound",
            "kind": "pytest_case",
            "path": test_path,
            "selector": positive_selector,
            "case": module_type,
            "pytest_nodeid": (
                f"{test_path}::{positive_selector}"
                f"[{module_type}]"
            ),
            "module_parameter": {"name": "module_type", "value": module_type},
            "sha256": test_sha256,
            "expected_outcome": positive_outcome,
            "case_contract": positive_contract,
        },
        "counterexample": {
            "disposition": "bound",
            "kind": "pytest_case",
            "path": test_path,
            "selector": counterexample_selector,
            "case": module_type,
            "pytest_nodeid": (
                f"{test_path}::{counterexample_selector}"
                f"[{module_type}]"
            ),
            "module_parameter": {"name": "module_type", "value": module_type},
            "sha256": test_sha256,
            "expected_outcome": counter_outcome,
            "case_contract": counter_contract,
        },
    }


def _source_first_behavior_bindings(
    root: Path,
    record: dict[str, Any],
    formula: dict[str, Any],
    module_type: str,
    source_contract: dict[str, Any],
) -> dict[str, Any]:
    test_path = "tests/test_module_semantics_batch_previously_grouped.py"
    if formula.get("residuals"):
        return _mechanical_behavior_bindings(
            root,
            record,
            formula,
            module_type,
            source_contract,
            test_path=test_path,
            positive_selector=(
                "test_source_first_reconstruction_matches_current_runtime"
            ),
            counterexample_selector=(
                "test_source_first_constructor_counterexample_still_fails"
            ),
            obligation_label="bounded source-first reconstruction",
        )

    behavior = formula.get("behavior_contract")
    if (
        not isinstance(behavior, dict)
        or behavior.get("kind") != "declaration_only"
        or source_contract.get("declaration_only") is not True
    ):
        raise ValueError(
            f"{module_type}: a zero-residual source-first formula must bind an "
            "actual declaration-only implementation"
        )
    test_sha256 = _sha256(root / test_path)
    component_id = str(record["bindings"]["instantiation"]["component_id"])
    parameters = copy.deepcopy(record["bindings"]["instantiation"]["parameters"])
    declared = [
        {
            key: item[key]
            for key in (
                "name",
                "unit",
                "lower_bound",
                "upper_bound",
                "initial_guess",
                "scale",
            )
        }
        for item in record["function_block"]["declared_variables"]
    ]
    positive_outcome = {
        "kind": "declaration_contract",
        "declared_variables": declared,
        "residual_count": 0,
    }
    positive_contract = {
        "runner_identity": ledger_checker.CASE_RUNNER_IDENTITY,
        "inputs": {
            "component_id": component_id,
            "parameters": parameters,
            "variables": {
                f"{component_id}.{item['name']}": item["initial_guess"]
                for item in declared
            },
            "external_variables": [],
        },
        "obligation": (
            f"{module_type} declares its exact mapped-variable contract and emits "
            "no residuals"
        ),
        "assertion_kind": "declaration_contract",
        "expected_fingerprint": ledger_checker._canonical_hash(positive_outcome),
        "expected_declarations": declared,
        "expected_residual_count": 0,
    }
    constructor_constraints = _mapping_list(
        formula["constraints"].get("constructor"),
        f"{module_type}.constraints.constructor",
    )
    protected_constraint = next(
        item
        for item in constructor_constraints
        if any(
            case.get("kind") == "outside"
            for case in item.get("cases", [])
            if isinstance(case, dict)
        )
    )
    outside_case = next(
        case
        for case in protected_constraint["cases"]
        if case.get("kind") == "outside"
    )
    configuration_names = {
        str(item["name"])
        for item in formula["configuration"]
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    bad_parameters = copy.deepcopy(parameters)
    bad_parameters.update(
        {
            name: value
            for name, value in outside_case["inputs"].items()
            if name in configuration_names
        }
    )
    counter_outcome = {
        "kind": "raises",
        "exception_type": protected_constraint["failure_type"],
        "message_selector": protected_constraint["message_selector"],
    }
    counter_contract = {
        "runner_identity": ledger_checker.CASE_RUNNER_IDENTITY,
        "inputs": {
            "component_id": component_id,
            "parameters": bad_parameters,
            "variables": {},
            "external_variables": [],
        },
        "obligation": f"{module_type} rejects its protected declaration contract",
        "assertion_kind": "raises",
        "expected_fingerprint": ledger_checker._canonical_hash(counter_outcome),
    }
    positive_selector = "test_source_first_reconstruction_matches_current_runtime"
    counter_selector = "test_source_first_constructor_counterexample_still_fails"
    return {
        "positive": {
            "disposition": "bound",
            "kind": "pytest_case",
            "path": test_path,
            "selector": positive_selector,
            "case": module_type,
            "pytest_nodeid": f"{test_path}::{positive_selector}[{module_type}]",
            "module_parameter": {"name": "module_type", "value": module_type},
            "sha256": test_sha256,
            "expected_outcome": positive_outcome,
            "case_contract": positive_contract,
        },
        "counterexample": {
            "disposition": "bound",
            "kind": "pytest_case",
            "path": test_path,
            "selector": counter_selector,
            "case": module_type,
            "pytest_nodeid": f"{test_path}::{counter_selector}[{module_type}]",
            "module_parameter": {"name": "module_type", "value": module_type},
            "sha256": test_sha256,
            "expected_outcome": counter_outcome,
            "case_contract": counter_contract,
        },
    }


def _compile_formula_semantics(
    root: Path,
    record: dict[str, Any],
    module_type: str,
    runtime_entry: dict[str, Any],
    source_fingerprint: str,
) -> tuple[dict[str, Any], str]:
    formula, relative_path, resource_sha256 = _load_scenario_formula(root, module_type)
    inputs, outputs = _formula_ports(formula, module_type, runtime_entry)
    source_semantics, implementation = _constructor_parameter_semantics(record, module_type)
    source_contract = ledger_checker._source_residual_contract(record, module_type)
    source_projection_aliases: dict[str, str] = {}
    if module_type in SOURCE_FIRST_MODULES:
        resolved_implementation = ledger_checker._resolve_python_symbol(
            module_type, implementation.get("python_symbol")
        )
        if resolved_implementation.get("error") or not inspect.isclass(
            resolved_implementation.get("value")
        ):
            raise ValueError(
                f"{module_type}: source-first implementation aliases are unavailable"
            )
        source_projection_aliases = (
            ledger_checker._configuration_attribute_parameters(
                resolved_implementation["value"]
            )
        )
    configuration = _formula_configuration(
        formula, module_type, source_semantics, implementation
    )
    updated = copy.deepcopy(record)
    updated["purpose"] = formula["purpose"]
    block = updated["function_block"]
    block["configuration"] = configuration

    base_symbols = {
        str(item["name"])
        for item in [*configuration, *inputs, *outputs]
    }
    current_residuals = {
        str(item["name"]): item
        for item in updated.get("residual_definitions", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    formula_residuals = _mapping_list(
        formula.get("residuals"),
        f"{module_type}.residuals",
        allow_empty=module_type in SOURCE_FIRST_MODULES,
    )
    if {str(item.get("name")) for item in formula_residuals} != set(current_residuals):
        raise ValueError(f"{module_type}: formula residual inventory is stale")
    compiled_residuals: list[dict[str, Any]] = []
    oracle_expressions: list[dict[str, Any]] = []
    residual_units: list[dict[str, Any]] = []
    zero_conditions: list[str] = []
    for formula_residual in formula_residuals:
        name = _string(formula_residual.get("name"), f"{module_type}.residual.name")
        direct_expression = _string(
            formula_residual.get("expression"), f"{module_type}.{name}.expression"
        )
        dimension = _string(
            formula_residual.get("dimension"), f"{module_type}.{name}.dimension"
        )
        dimension, unit = _validate_dimension_unit(
            dimension, formula_residual.get("unit"), f"{module_type}.{name}"
        )
        dimensional_derivation = _string(
            formula_residual.get("dimensional_derivation"),
            f"{module_type}.{name}.dimensional_derivation",
        )
        scale_expression = _string(
            formula_residual.get("scale_expression"), f"{module_type}.{name}.scale_expression"
        )
        zero_conditions.append(
            _string(formula_residual.get("zero_condition"), f"{module_type}.{name}.zero_condition")
        )
        residual = copy.deepcopy(current_residuals[name])
        source_intermediates: list[dict[str, Any]] = []
        intermediate_names: set[str] = set()
        declared_intermediates = formula_residual.get("source_intermediates")
        if declared_intermediates is None and module_type in SOURCE_FIRST_MODULES:
            source_intermediates = copy.deepcopy(residual.get("intermediates", []))
            intermediate_names = {
                str(item["symbol"])
                for item in source_intermediates
                if isinstance(item, dict) and isinstance(item.get("symbol"), str)
            }
            implementation_symbols = base_symbols | intermediate_names
            for item in source_intermediates:
                if not isinstance(item, dict):
                    continue
                item["binding_kind"] = "implementation_source_projection"
                item["expression"] = (
                    _normalize_implementation_projection_expression(
                        str(item.get("expression", "")),
                        source_projection_aliases,
                    )
                )
                item["dependencies"] = sorted(
                    (
                        ledger_checker._expression_identifiers(
                            str(item.get("expression", ""))
                        )
                        - ledger_checker.EXPRESSION_BUILTINS
                    )
                    & implementation_symbols
                )
            declared_intermediates = []
        for intermediate in _mapping_list(
            declared_intermediates or [],
            f"{module_type}.{name}.source_intermediates",
            allow_empty=True,
        ):
            symbol = _string(intermediate.get("symbol"), f"{module_type}.{name}.intermediate.symbol")
            expression = _string(
                intermediate.get("expression"), f"{module_type}.{name}.{symbol}.expression"
            )
            if symbol in base_symbols or symbol in intermediate_names:
                raise ValueError(f"{module_type}.{name}: duplicate intermediate {symbol}")
            dependencies = sorted(
                ledger_checker._expression_identifiers(expression)
                - ledger_checker.EXPRESSION_BUILTINS
            )
            if set(dependencies) - (base_symbols | intermediate_names):
                raise ValueError(
                    f"{module_type}.{name}.{symbol}: intermediate leaves the formula symbol universe"
                )
            source_intermediates.append(
                {"symbol": symbol, "expression": expression, "dependencies": dependencies}
            )
            intermediate_names.add(symbol)
        residual["intermediates"] = source_intermediates
        if module_type in (MECHANICAL_DRAFT_MODULES | SOURCE_FIRST_MODULES):
            _complete_source_branch_projection(residual, source_contract)
        if module_type in SOURCE_FIRST_MODULES:
            for branch in residual.get("branches", []):
                if isinstance(branch, dict):
                    for field in ("condition", "expression"):
                        branch[field] = (
                            _normalize_implementation_projection_expression(
                                str(branch.get(field, "")),
                                source_projection_aliases,
                            )
                        )
                    branch["binding_kind"] = (
                        "implementation_source_projection"
                    )
        source_dependency_symbols = (
            ledger_checker._expression_identifiers(str(residual["expression"]))
            - ledger_checker.EXPRESSION_BUILTINS
        )
        for branch in residual.get("branches", []):
            if not isinstance(branch, dict):
                continue
            for field in ("condition", "expression"):
                source_dependency_symbols.update(
                    (
                        ledger_checker._expression_identifiers(
                            str(branch.get(field, ""))
                        )
                        - ledger_checker.EXPRESSION_BUILTINS
                    )
                    & (base_symbols | intermediate_names)
                )
        source_dependencies = sorted(source_dependency_symbols)
        if set(source_dependencies) - (base_symbols | intermediate_names):
            raise ValueError(f"{module_type}.{name}: source expression dependencies are unresolved")
        direct_dependencies = sorted(
            ledger_checker._expression_identifiers(direct_expression)
            - ledger_checker.EXPRESSION_BUILTINS
        )
        if set(direct_dependencies) - base_symbols:
            raise ValueError(f"{module_type}.{name}: oracle expression leaves the formula symbol universe")
        scale_dependencies = (
            ledger_checker._expression_identifiers(scale_expression)
            - ledger_checker.EXPRESSION_BUILTINS
        )
        if not scale_dependencies or scale_dependencies - base_symbols:
            raise ValueError(
                f"{module_type}.{name}: oracle scale leaves the declared formula symbol universe"
            )
        residual["dependencies"] = source_dependencies
        residual["intermediates"] = source_intermediates
        runtime_name = formula_residual.get("runtime_name")
        if runtime_name is not None:
            residual["runtime_name"] = _string(
                runtime_name, f"{module_type}.{name}.runtime_name"
            )
        else:
            residual.pop("runtime_name", None)
        residual["scale"]["unit"] = unit
        residual["dimensional_derivation"] = dimensional_derivation
        source_role_literal = source_contract.get("roles", {}).get(name)
        source_role_expression = source_contract.get("role_expressions", {}).get(name)
        if source_role_literal in {"equation", "soft_check", "post_check"}:
            residual["role"] = source_role_literal
        elif (
            source_role_literal not in {"equation", "soft_check", "post_check"}
            and source_role_expression
        ):
            residual["role"] = {
                "expression": source_role_expression,
                "cases": [
                    {"when": "equation", "value": "equation"},
                    {"when": "soft_check", "value": "soft_check"},
                    {"when": "post_check", "value": "post_check"},
                ],
            }
        compiled_residuals.append(residual)
        oracle_expressions.append(
            {
                "name": name,
                "expression": direct_expression,
                "dependencies": direct_dependencies,
                "unit": unit,
                "scale_expression": scale_expression,
                "dimensional_derivation": dimensional_derivation,
            }
        )
        residual_units.append(
            {
                "symbol": name,
                "unit": unit,
                "kind": "residual",
                "reference": {
                    "convention_identity": UNIT_CONVENTION_IDENTITY,
                    "dimension": dimension,
                    "unit": unit,
                },
            }
        )
    updated["residual_definitions"] = compiled_residuals
    block["outputs"]["residuals"] = [
        str(item["name"]) for item in compiled_residuals
    ]

    unit_items: list[dict[str, Any]] = []
    for kind, items in (
        ("configuration", formula.get("configuration", [])),
        ("declared_variable", [*inputs, *outputs]),
    ):
        for item in items:
            item_kind = (
                "external_input"
                if kind == "declared_variable" and item.get("source_kind") == "external"
                else kind
            )
            unit_items.append(
                {
                    "symbol": item["name"],
                    "unit": item["unit"],
                    "kind": item_kind,
                    "reference": {
                        "convention_identity": UNIT_CONVENTION_IDENTITY,
                        "dimension": item["dimension"],
                        "unit": item["unit"],
                    },
                }
            )
    units_by_symbol: dict[str, dict[str, Any]] = {
        str(item["symbol"]): item for item in unit_items
    }
    for residual_unit in residual_units:
        symbol = str(residual_unit["symbol"])
        existing = units_by_symbol.get(symbol)
        if existing is None:
            units_by_symbol[symbol] = residual_unit
            continue
        if (
            existing.get("kind") != "declared_variable"
            or existing.get("unit") != residual_unit.get("unit")
            or existing.get("reference") != residual_unit.get("reference")
        ):
            raise ValueError(
                f"{module_type}.{symbol}: declared-variable/residual unit identities conflict"
            )
        existing["kind"] = "declared_variable_residual"
    updated["symbol_units"] = list(units_by_symbol.values())
    updated["unit_convention"] = _project_unit_convention(root)
    updated["constraints"] = _compile_formula_constraints(
        formula, module_type, source_fingerprint
    )
    updated["regions"] = _compile_formula_regions(formula, module_type)
    updated["assumptions"] = _string_list(
        formula.get("assumptions"), f"{module_type}.assumptions"
    )
    formula_invariants = _string_list(
        formula.get("invariants", []),
        f"{module_type}.invariants",
        allow_empty=True,
    )
    updated["invariants"] = [
        *zero_conditions,
        *formula_invariants,
        (
            "Evaluation is side-effect free: it reads one explicit current vector and "
            "returns residual records without mutating solver variables or hidden state."
        ),
    ]
    validity = _string_list(formula.get("validity"), f"{module_type}.validity")
    block["preconditions"] = [
        *validity,
        *(
            item["predicate"]
            for group in ("constructor", "evaluation")
            for item in updated["constraints"][group]
        ),
    ]
    block["failures"] = [
        item["on_violation"]
        for group in ("constructor", "evaluation")
        for item in updated["constraints"][group]
    ]
    if module_type in (MECHANICAL_DRAFT_MODULES | SOURCE_FIRST_MODULES):
        require_behavior = module_type in SOURCE_FIRST_MODULES
        block["effects"] = _string_list(
            formula.get("effects"),
            f"{module_type}.effects",
            allow_empty=not require_behavior,
        )
        block["postconditions"] = _string_list(
            formula.get("postconditions"),
            f"{module_type}.postconditions",
            allow_empty=not require_behavior,
        )
        block["termination"] = _string(
            formula.get("termination"), f"{module_type}.termination"
        )

    is_mechanical_draft = module_type in MECHANICAL_DRAFT_MODULES
    is_source_first = module_type in SOURCE_FIRST_MODULES
    is_unlicensed_reconstruction = is_mechanical_draft or is_source_first
    if is_source_first:
        behavior_contract = formula.get("behavior_contract")
        if not isinstance(behavior_contract, dict):
            raise ValueError(
                f"{module_type}: source-first formula must declare a behavior_contract"
            )
        updated["behavior_contract"] = copy.deepcopy(behavior_contract)
    formula_resource = {
        "kind": (
            "mechanical_semantic_draft"
            if is_mechanical_draft
            else (
                "source_first_semantic_reconstruction"
                if is_source_first
                else "physical_formula"
            )
        ),
        "disposition": "bound",
        "identity": f"physicsguard.project_formula.{module_type}.v1",
        "path": relative_path,
        "selector": f"module_type: {module_type}",
        "sha256": resource_sha256,
        "implementation_binding": {
            **implementation,
            "source_semantic_ir_fingerprint": source_fingerprint,
        },
        "parameter_semantics": copy.deepcopy(configuration),
        "dimensional_derivations": [
            {
                "residual": item["name"],
                "dimension": item["dimension"],
                "unit": item["unit"],
                "derivation": item["dimensional_derivation"],
            }
            for item in formula_residuals
        ],
    }
    if is_unlicensed_reconstruction:
        formula_resource.update(
            {
                "authoring_status": formula["authoring_status"],
                "separate_review_status": formula["separate_review_status"],
                "physical_claim_licensed": False,
                "claim_boundary": formula["claim_boundary"],
            }
        )
    bindings = updated["bindings"]
    if is_mechanical_draft:
        bindings["behavioral_tests"] = _mechanical_behavior_bindings(
            root, updated, formula, module_type, source_contract
        )
    elif is_source_first:
        bindings["behavioral_tests"] = _source_first_behavior_bindings(
            root, updated, formula, module_type, source_contract
        )
    if is_unlicensed_reconstruction:
        literal_selector = f"type: {module_type}"
        instantiation_path = root / str(bindings["instantiation"]["path"])
        if literal_selector not in instantiation_path.read_text(encoding="utf-8"):
            raise ValueError(
                f"{module_type}: exact instantiation lacks its literal type selector"
            )
        bindings["instantiation"]["selector"] = literal_selector
    bindings["resources"] = [formula_resource]
    if is_source_first and not formula_residuals:
        bindings["oracle"] = {
            "disposition": "not_applicable",
            "kind": "declaration_only_no_equation",
            "applicability_kind": "declaration_only_no_equation",
            "reason": (
                "The current implementation declares mapped variables and emits no "
                "ResidualRecord; its non-empty behavior contract is tested directly."
            ),
            "behavior_contract_fingerprint": ledger_checker._canonical_hash(
                updated["behavior_contract"]
            ),
        }
    else:
        bindings["oracle"] = {
            "disposition": "bound",
            "kind": "analytic_expression",
            "owner": formula["owner"],
            "independent_from_implementation": not is_unlicensed_reconstruction,
            "authority": {
                "kind": "project_formula",
                "path": relative_path,
                "selector": f"module_type: {module_type}",
                "sha256": resource_sha256,
            },
            "expressions": oracle_expressions,
            "cases": copy.deepcopy(
                _mapping_list(
                    formula.get("oracle_cases"), f"{module_type}.oracle_cases"
                )
            ),
        }
    if is_unlicensed_reconstruction and formula_residuals:
        bindings["oracle"].update(
            {
                "independence_status": "pending_separate_review",
                "physical_claim_licensed": False,
                "claim_boundary": formula["claim_boundary"],
            }
        )
    source_paths = [
        bindings["implementation"].get("path"),
        bindings["behavioral_tests"]["positive"].get("path"),
        bindings["behavioral_tests"]["counterexample"].get("path"),
        bindings["instantiation"].get("path"),
        relative_path,
        ledger_checker.RUNTIME_PORT_REGISTRY_PATH,
        ledger_checker.UNIT_CONVENTION_REGISTRY_PATH,
    ]
    updated["provenance"] = {
        "authoring_mode": (
            "source_first_reconstruction_pending_independent_review"
            if module_type in SOURCE_FIRST_MODULES
            else "source_formula_test_compilation_pending_independent_review"
        ),
        "author_owner": "physicsguard.module_semantics.author.current",
        "inputs": list(dict.fromkeys(str(item) for item in source_paths if item)),
    }
    updated["stale_triggers"] = [
        "live registry, exact instantiation, scenario boundary, or runtime port contract changes",
        "implementation recursive source semantic IR, equation, scale, role, diagnostic, or protected guard changes",
        "project formula, SI convention, behavior-case contract, or oracle case changes",
        "independent reviewer provider, request, result, or receipt changes",
    ]
    return updated, relative_path


def _read_exact(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _atomic_write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f"{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_ledger(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    if not isinstance(payload, dict) or not isinstance(payload.get("module_records"), list):
        raise ValueError("the current module semantics ledger is missing or malformed")
    records: dict[str, dict[str, Any]] = {}
    for item in payload["module_records"]:
        if not isinstance(item, dict) or not isinstance(item.get("module_type"), str):
            raise ValueError("the current ledger contains a malformed module record")
        module_type = str(item["module_type"])
        if module_type in records:
            raise ValueError(f"the current ledger duplicates {module_type}")
        records[module_type] = item
    missing = sorted(COMPILED_MODULES - records.keys())
    if missing:
        raise ValueError(f"the compiler batch is missing ledger records: {missing}")
    return payload, records


def _entry_by_module(runtime_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = runtime_payload.get("modules")
    if not isinstance(entries, list):
        raise ValueError("the generated runtime-port registry has no module inventory")
    result = {
        str(item["module_type"]): item
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("module_type"), str)
    }
    if len(result) != len(entries):
        raise ValueError("the generated runtime-port registry has duplicate or invalid modules")
    resolved = {
        module_type
        for module_type, item in result.items()
        if item.get("disposition") == "resolved"
    }
    if resolved != COMPILED_MODULES:
        raise ValueError(
            "the current resolved runtime-role batch changed without compiler review: "
            f"expected={sorted(COMPILED_MODULES)}, actual={sorted(resolved)}"
        )
    return result


def _ordered_names(current: Any, expected: set[str]) -> list[str]:
    if (
        isinstance(current, list)
        and all(isinstance(item, str) for item in current)
        and len(current) == len(set(current))
        and set(current) == expected
    ):
        return list(current)
    return sorted(expected)


def _synchronize_source_observations(
    root: Path,
    record: dict[str, Any],
    module_type: str,
    runtime_entry: dict[str, Any],
) -> tuple[dict[str, Any], str, str | None]:
    updated = copy.deepcopy(record)
    source_contract = ledger_checker._source_residual_contract(record, module_type)
    semantic_ir_errors = source_contract.get("semantic_ir_errors")
    semantic_ir_fingerprint = source_contract.get("semantic_ir_fingerprint")
    if semantic_ir_errors or not isinstance(semantic_ir_fingerprint, str):
        raise ValueError(
            f"{module_type}: recursive source semantic IR is unresolved: "
            f"{semantic_ir_errors or ['missing fingerprint']}"
        )
    updated["source_semantic_ir"] = {
        "schema": SOURCE_IR_SCHEMA,
        "fingerprint": semantic_ir_fingerprint,
    }

    block = updated.get("function_block")
    if not isinstance(block, dict):
        raise ValueError(f"{module_type}: function_block must exist before compilation")
    declared_ports = runtime_entry.get("declared_ports")
    external_ports = runtime_entry.get("external_ports", [])
    ports = runtime_entry.get("ports")
    if (
        not isinstance(declared_ports, list)
        or not isinstance(external_ports, list)
        or not isinstance(ports, list)
    ):
        raise ValueError(f"{module_type}: resolved runtime-port evidence is malformed")
    declared_by_name = {
        str(item["name"]): item
        for item in declared_ports
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    roles = {
        str(item["name"]): str(item["direction"])
        for item in ports
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("direction"), str)
    }
    external_by_name = {
        str(item["name"]): item
        for item in external_ports
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if (
        set(declared_by_name) | set(external_by_name) != set(roles)
        or set(declared_by_name) & set(external_by_name)
        or len(declared_by_name) != len(declared_ports)
        or len(external_by_name) != len(external_ports)
    ):
        raise ValueError(f"{module_type}: role authority does not exactly cover live ports")

    current_declared = block.get("declared_variables")
    current_by_name = {
        str(item["name"]): item
        for item in current_declared
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    } if isinstance(current_declared, list) else {}
    if set(current_by_name) == set(declared_by_name) and len(current_by_name) == len(current_declared):
        order = [str(item["name"]) for item in current_declared]
    else:
        order = sorted(declared_by_name)
    synchronized_variables: list[dict[str, Any]] = []
    for name in order:
        observed = declared_by_name[name]
        item = copy.deepcopy(current_by_name.get(name, {}))
        item.update(
            {
                "name": name,
                "unit": observed.get("unit"),
                "role": roles[name],
                "lower_bound": observed.get("lower_bound"),
                "upper_bound": observed.get("upper_bound"),
                "initial_guess": observed.get("initial_guess"),
                "scale": observed.get("scale"),
            }
        )
        synchronized_variables.append(item)
    block["declared_variables"] = synchronized_variables
    block["external_inputs"] = [
        {
            "name": name,
            "unit": external_by_name[name].get("unit"),
            "role": roles[name],
            "source_attribute": external_by_name[name].get("source_attribute"),
            "source_index": external_by_name[name].get("source_index"),
            "source_reference": external_by_name[name].get("source_reference"),
        }
        for name in sorted(external_by_name)
    ]

    state = block.get("state")
    if not isinstance(state, dict):
        raise ValueError(f"{module_type}: state projection must exist before compilation")
    state_roles = {
        "previous": "state_previous",
        "current": "state_current",
        "next": "state_next",
    }
    for slot, role in state_roles.items():
        expected = {
            name
            for name, direction in roles.items()
            if name in declared_by_name and direction == role
        }
        state[slot] = _ordered_names(state.get(slot), expected)

    outputs = block.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError(f"{module_type}: output projection must exist before compilation")
    expected_outputs = {
        name
        for name, direction in roles.items()
        if name in declared_by_name and direction in {"output", "state_next"}
    }
    outputs["declared_variables"] = _ordered_names(
        outputs.get("declared_variables"), expected_outputs
    )
    block["role_authority"] = runtime_ports.resolved_role_authority_binding(
        runtime_entry
    )

    formula_path: str | None = None
    if module_type in FORMULA_MODULES:
        updated, formula_path = _compile_formula_semantics(
            root,
            updated,
            module_type,
            runtime_entry,
            semantic_ir_fingerprint,
        )

    review = updated.get("semantic_review")
    if not isinstance(review, dict):
        raise ValueError(f"{module_type}: semantic_review must remain explicit")
    if review.get("status") != "pending" or review.get("license") != "unlicensed":
        raise ValueError(
            f"{module_type}: compiler cannot modify or consume a licensed review state"
    )
    review["subject_fingerprint"] = ledger_checker._record_fingerprint(updated)
    return updated, semantic_ir_fingerprint, formula_path


def _changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(_changed_paths(before[key], after[key], path))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        return [] if before == after else [prefix]
    return [] if before == after else [prefix]


def _path_is_compiler_owned(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}.") for prefix in COMPILER_OWNED_PATH_PREFIXES)


def _render_record(record: dict[str, Any], newline: str) -> str:
    rendered = yaml.safe_dump(
        record,
        sort_keys=False,
        allow_unicode=True,
        width=110,
    ).rstrip("\n")
    lines = rendered.split("\n")
    return newline.join([f"- {lines[0]}", *(f"  {line}" for line in lines[1:])]) + newline


def _splice_records(
    original_text: str,
    updated_records: dict[str, dict[str, Any]],
) -> str:
    starts = list(re.finditer(r"(?m)^- module_type: ([^\r\n]+)\r?$", original_text))
    if not starts:
        raise ValueError("the current ledger has no spliceable module records")
    newline = "\r\n" if original_text.count("\r\n") >= original_text.count("\n") / 2 else "\n"
    pieces: list[str] = []
    cursor = 0
    replaced: set[str] = set()
    for index, match in enumerate(starts):
        module_type = match.group(1).strip()
        end = starts[index + 1].start() if index + 1 < len(starts) else len(original_text)
        pieces.append(original_text[cursor:match.start()])
        if module_type in updated_records:
            pieces.append(_render_record(updated_records[module_type], newline))
            replaced.add(module_type)
        else:
            pieces.append(original_text[match.start():end])
        cursor = end
    pieces.append(original_text[cursor:])
    missing = sorted(updated_records.keys() - replaced)
    if missing:
        raise ValueError(f"the ledger splice could not find records: {missing}")
    return "".join(pieces)


def compile_outputs(
    root: Path = ROOT,
    ledger_path: Path = DEFAULT_LEDGER,
) -> tuple[str, str, dict[str, Any]]:
    _, records = _load_ledger(ledger_path)
    runtime_payload = runtime_ports.build_registry_payload(root, ledger_path)
    runtime_entries = _entry_by_module(runtime_payload)
    updated_records: dict[str, dict[str, Any]] = {}
    module_reports: list[dict[str, Any]] = []
    for module_type in sorted(COMPILED_MODULES):
        before = records[module_type]
        after, source_fingerprint, formula_path = _synchronize_source_observations(
            root,
            before,
            module_type,
            runtime_entries[module_type],
        )
        changed_paths = _changed_paths(before, after)
        foreign_paths = [path for path in changed_paths if not _path_is_compiler_owned(path)]
        if foreign_paths:
            raise ValueError(
                f"{module_type}: compiler attempted to change domain-owned paths: {foreign_paths}"
            )
        updated_records[module_type] = after
        module_reports.append(
            {
                "module_type": module_type,
                "batch": (
                    "gold"
                    if module_type in GOLD_MODULES
                    else (
                        "mechanical_draft_pending_independent_review"
                        if module_type in MECHANICAL_DRAFT_MODULES
                        else (
                            "source_first_reconstruction_pending_independent_review"
                            if module_type in SOURCE_FIRST_MODULES
                            else "exact_scenario_role"
                        )
                    )
                ),
                "source_semantic_ir_fingerprint": source_fingerprint,
                "runtime_role_authority": runtime_entries[module_type]["role_authority_basis"],
                "formula_authority": formula_path,
                "changed_paths": changed_paths,
            }
        )

    original_ledger = _read_exact(ledger_path)
    compiled_ledger = _splice_records(original_ledger, updated_records)
    runtime_rendered = runtime_ports._render(runtime_payload)
    runtime_newline = "\r\n" if os.linesep == "\r\n" else "\n"
    runtime_rendered = runtime_rendered.replace("\n", runtime_newline)
    report = {
        "schema": "physicsguard.module_semantics_compilation_report.v1",
        "compiler_identity": COMPILER_IDENTITY,
        "compiled_module_count": len(COMPILED_MODULES),
        "gold_module_count": len(GOLD_MODULES),
        "exact_scenario_role_module_count": len(SCENARIO_ROLE_MODULES),
        "mechanical_draft_module_count": len(MECHANICAL_DRAFT_MODULES),
        "source_first_reconstruction_module_count": len(SOURCE_FIRST_MODULES),
        "source_semantic_ir_bound_count": len(module_reports),
        "source_semantic_ir_error_count": 0,
        "runtime_registry": {
            "module_count": len(runtime_payload["modules"]),
            "resolved_count": sum(
                item["disposition"] == "resolved" for item in runtime_payload["modules"]
            ),
            "unresolved_count": sum(
                item["disposition"] == "unresolved" for item in runtime_payload["modules"]
            ),
            "registry_fingerprint": runtime_payload["registry_fingerprint"],
        },
        "preserved_domain_paths": list(PRESERVED_DOMAIN_PATHS),
        "modules": module_reports,
    }
    return compiled_ledger, runtime_rendered, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile source-observed module semantics for the reviewed 4+15 batch "
            "plus the bounded 22-module mechanical-draft batch without inferring or "
            "licensing physical meaning."
        )
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--runtime-output", type=Path, default=DEFAULT_RUNTIME_REGISTRY
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    compiled_ledger, compiled_runtime, report = compile_outputs(ROOT, args.ledger)
    ledger_current = _read_exact(args.ledger) == compiled_ledger
    runtime_current = (
        args.runtime_output.is_file()
        and _read_exact(args.runtime_output) == compiled_runtime
    )
    report["ledger_current"] = ledger_current
    report["runtime_registry_current"] = runtime_current
    if args.check:
        report["status"] = "pass" if ledger_current and runtime_current else "stale"
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if ledger_current and runtime_current else 1

    _atomic_write_exact(args.runtime_output, compiled_runtime)
    _atomic_write_exact(args.ledger, compiled_ledger)
    verified_ledger, verified_runtime, verified_report = compile_outputs(ROOT, args.ledger)
    if (
        _read_exact(args.ledger) != verified_ledger
        or _read_exact(args.runtime_output) != verified_runtime
    ):
        raise RuntimeError("post-apply source-first compilation is not deterministic")
    verified_report.update(
        {
            "ledger_current": True,
            "runtime_registry_current": True,
            "status": "pass",
        }
    )
    print(json.dumps(verified_report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
