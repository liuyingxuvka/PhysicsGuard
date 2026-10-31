"""Residual records and assembly."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import math
from typing import Any, Optional

import numpy as np

from physicsguard.core.assumptions import AssumptionCard, AssumptionManager, AssumptionSummary
from physicsguard.core._residual_dependencies import Dependencies, module_residual_dependencies
from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.modules.registry import ModuleRegistry, instantiate_module_with_parameter_reads, default_module_registry
from physicsguard.schema.system_spec import SystemSpec, VariableOverrideSpec


SUPPORTED_RESIDUAL_ROLES = frozenset(
    {"equation", "connection", "boundary", "assumption", "soft_check", "post_check"}
)
DEFAULT_SOLVER_RESIDUAL_ROLES = frozenset({"equation", "connection", "boundary", "assumption"})


@dataclass(frozen=True)
class ResidualRecord:
    name: str
    value: float
    scale: float
    source: str
    role: str = "equation"
    diagnostic_key: Optional[str] = None
    description: Optional[str] = None
    active_in_solver: Optional[bool] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("residual name cannot be empty")
        if self.role not in SUPPORTED_RESIDUAL_ROLES:
            raise ValueError(
                f"{self.name}: residual role must be one of "
                f"{', '.join(sorted(SUPPORTED_RESIDUAL_ROLES))}"
            )
        if self.role == "post_check" and self.active_in_solver:
            raise ValueError(f"{self.name}: post_check residuals cannot enter the solver")
        if not math.isfinite(self.value):
            raise ValueError(f"{self.name}: residual value must be finite")
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError(f"{self.name}: residual scale must be finite and positive")
        if not math.isfinite(self.normalized_value):
            raise ValueError(f"{self.name}: normalized residual must be finite")

    @property
    def normalized_value(self) -> float:
        return self.value / self.scale

    @property
    def abs_normalized_value(self) -> float:
        return abs(self.normalized_value)

    @property
    def participates_in_solver(self) -> bool:
        if self.role in DEFAULT_SOLVER_RESIDUAL_ROLES:
            return True
        if self.role == "soft_check":
            return bool(self.active_in_solver)
        return False


class ResidualBuilder:
    """Build variables and normalized residual vectors for a SystemSpec."""

    def __init__(self, system: SystemSpec, module_registry: ModuleRegistry | None = None) -> None:
        self.assumption_manager = AssumptionManager(system)
        self.system = self.assumption_manager.apply_parameter_assumptions(system)
        self.module_registry = module_registry or default_module_registry()
        self._modules = None
        self._registry: Optional[VariableRegistry] = None

    def assumption_cards(self) -> list[AssumptionCard]:
        return self.assumption_manager.assumption_cards()

    def assumption_summary(self) -> AssumptionSummary:
        return self.assumption_manager.build_summary()

    def build_modules(self):
        if self._modules is None:
            self._modules = [self._module_from_component(component) for component in self.system.components]
        return self._modules

    def build_registry(self) -> VariableRegistry:
        if self._registry is not None:
            return self._registry
        registry = VariableRegistry()
        component_by_id = {component.id: component for component in self.system.components}
        for module in self.build_modules():
            component = component_by_id[module.component_id]
            for record in module.declare_variables():
                if record.name.split(".", 1)[0] != module.component_id:
                    raise ValueError(
                        f"{module.component_id}: declared variable '{record.name}' "
                        "must be owned by the declaring component"
                    )
                registry.add_variable(self._apply_override(record, component.variable_overrides))
        self._registry = registry
        return registry

    def solver_residual_records(self, x: np.ndarray) -> list[ResidualRecord]:
        return [
            record
            for record in self.diagnostic_residual_records(x)
            if record.participates_in_solver
        ]

    def diagnostic_residual_records(
        self,
        x: np.ndarray,
        *,
        _dependencies: list[Dependencies] | None = None,
        _zero_reads: list[str] | None = None,
        _locations: list[tuple[Any, int]] | None = None,
    ) -> list[ResidualRecord]:
        registry = self.build_registry()
        vector = self._validate_x(x, registry)
        records: list[ResidualRecord] = []
        for module in self.build_modules():
            if _dependencies is None:
                current = module.residuals(vector, registry)
            else:
                current, dependencies, no_reads = module_residual_dependencies(module, vector, registry, ResidualRecord)
                if no_reads and _zero_reads is not None:
                    _zero_reads.append(module.module_type)
                # A supported no-read native formula falls back to declared
                # variables. Unknown custom provenance remains None, even for [].
                declared = frozenset(record.name for record in module.declare_variables())
                dependencies = [declared if no_reads and value == frozenset() else value for value in dependencies]
                _dependencies.extend(dependencies)
            records.extend(current)
            if _locations is not None:
                _locations.extend((module, index) for index in range(len(current)))
        for kind, group in (
            ("connection", self._connection_residuals(vector, registry)),
            ("boundary", self._boundary_residuals(vector, registry)),
            ("assumption", self.assumption_manager.assumption_residual_records(vector, registry, self.system)),
        ):
            records.extend(group)
            if _locations is not None:
                _locations.extend((kind, index) for index in range(len(group)))
            if _dependencies is not None:
                for record in group:
                    if record.source == "connection":
                        _dependencies.append(frozenset(record.name.removeprefix("connection:").split("=")))
                    else:
                        _dependencies.append(frozenset({record.name.split(":", 1)[1]}))
        normalized = np.array([record.normalized_value for record in records], dtype=float)
        if not np.all(np.isfinite(normalized)):
            raise ValueError("residual vector contains NaN or inf")
        return records

    def residual_vector(self, x: np.ndarray) -> np.ndarray:
        values = np.array(
            [record.normalized_value for record in self.solver_residual_records(x)],
            dtype=float,
        )
        if values.ndim != 1 or not np.all(np.isfinite(values)):
            raise ValueError("residual vector contains NaN or inf")
        return values

    def residual_scale_defaults(
        self,
        x: np.ndarray,
        records: list[ResidualRecord],
        locations: list[tuple[Any, int]],
    ) -> list[bool | None]:
        """Classify native module scales at this configuration; None is unsupported.

        Records and locations are aligned diagnostic occurrences, including a
        checked subset. Framework constraints are not module defaults. Each module is
        reconstructed with its actual, post-assumption parameters, then numeric
        constructor reads are varied independently while only scales are read.
        """
        if len(records) != len(locations):
            return [None] * len(records)
        registry = self.build_registry()
        vector = self._validate_x(x, registry)
        defaults: list[bool | None] = [False if isinstance(owner, str) else None for owner, _ in locations]
        groups: dict[int, tuple[Any, list[tuple[int, int]]]] = {}
        for position, (owner, index) in enumerate(locations):
            if not isinstance(owner, str):
                groups.setdefault(id(owner), (owner, []))[1].append((position, index))
        components = {component.id: component for component in self.system.components}

        def identities(rows: list[ResidualRecord]) -> list[tuple[str, str, str, str | None]]:
            return [(row.name, row.source, row.role, row.diagnostic_key) for row in rows]

        for module, positions in groups.values():
            # Custom implementations keep a numeric estimate but do not inherit native scale provenance.
            if not type(module).__module__.startswith("physicsguard.modules."):
                continue
            try:
                component = components[module.component_id]
                parameters = component.parameters
                reads: dict[str, Any] = {}
                native = instantiate_module_with_parameter_reads(
                    self.module_registry, component.type, deepcopy(parameters), reads, component.id,
                )
                baseline = native.residuals(vector, registry)
                if any(not isinstance(index, int) or index < 0 or index >= len(baseline) for _, index in positions):
                    continue
                actual = [records[position] for position, _ in positions]
                expected = [baseline[index] for _, index in positions]
                if (identities(actual) != identities(expected)
                        or any(a.scale != b.scale for a, b in zip(actual, expected))):
                    continue
                contributors: list[set[str]] = [set() for _ in baseline]
                supported = True
                compound_reads = False
                for key, default in reads.items():
                    value = parameters.get(key, default)
                    if isinstance(value, (dict, list, tuple)):
                        compound_reads = True
                        continue
                    if isinstance(value, bool):
                        continue
                    numeric = value
                    if isinstance(value, str):
                        try:
                            numeric = float(value)
                        except ValueError:
                            continue
                    if not isinstance(numeric, (int, float)) or not math.isfinite(numeric):
                        continue
                    candidates = (numeric + 1, numeric - 1) if isinstance(numeric, int) else (
                        (numeric * 2, numeric / 2) if numeric else (1.0, -1.0)
                    )
                    replayed = False
                    for candidate in candidates:
                        if candidate == numeric or not math.isfinite(candidate):
                            continue
                        trial = deepcopy(parameters)
                        trial[key] = str(candidate) if isinstance(value, str) else candidate
                        try:
                            changed = self.module_registry.create(component.type, component.id, trial).residuals(vector, registry)
                        except Exception:
                            continue
                        if identities(changed) != identities(baseline):
                            supported = False
                            break
                        replayed = True
                        for index, row in enumerate(changed):
                            if row.scale != baseline[index].scale:
                                contributors[index].add(key)
                    if not supported or not replayed:
                        supported = False
                        break
                if supported:
                    for position, index in positions:
                        if contributors[index]:
                            defaults[position] = any(key not in parameters for key in contributors[index])
                        elif not compound_reads:
                            defaults[position] = True
            except Exception:
                # A custom constructor or residual replay cannot license a scale claim.
                continue
        return defaults

    def _module_from_component(self, component):
        return self.module_registry.create(component.type, component.id, component.parameters)

    def _apply_override(
        self,
        record: VariableRecord,
        overrides: dict[str, VariableOverrideSpec],
    ) -> VariableRecord:
        keys = [record.local_name, record.name]
        override = next((overrides[key] for key in keys if key and key in overrides), None)
        if override is None:
            return record
        updated = record
        for field_name in ("lower_bound", "upper_bound", "initial_guess", "scale"):
            value = getattr(override, field_name)
            if value is not None:
                updated = replace(updated, **{field_name: value})
        return updated

    def _validate_x(self, x: np.ndarray, registry: VariableRegistry) -> np.ndarray:
        vector = np.asarray(x, dtype=float)
        if vector.ndim != 1 or vector.shape[0] != registry.size():
            raise ValueError(
                f"solver vector length {vector.shape[0] if vector.ndim else 1} "
                f"does not match registry size {registry.size()}"
            )
        if not np.all(np.isfinite(vector)):
            raise ValueError("solver vector contains NaN or inf")
        return vector

    def _connection_residuals(
        self,
        x: np.ndarray,
        registry: VariableRegistry,
    ) -> list[ResidualRecord]:
        records: list[ResidualRecord] = []
        for connection in self.system.connections:
            try:
                from_index = registry.get_index(connection.from_variable)
                to_index = registry.get_index(connection.to_variable)
                from_record = registry.get_record(connection.from_variable)
                to_record = registry.get_record(connection.to_variable)
            except KeyError as exc:
                raise KeyError(f"connection references unknown variable: {exc}") from exc
            scale = (
                connection.scale
                if connection.scale is not None
                else 1e-6 * max(from_record.scale, to_record.scale)
            )
            records.append(
                ResidualRecord(
                    name=f"connection:{connection.from_variable}={connection.to_variable}",
                    value=float(x[from_index] - x[to_index]),
                    scale=scale,
                    source="connection",
                    role="connection",
                    diagnostic_key="connection_mismatch",
                    description=connection.description,
                )
            )
        return records

    def _boundary_residuals(
        self,
        x: np.ndarray,
        registry: VariableRegistry,
    ) -> list[ResidualRecord]:
        records: list[ResidualRecord] = []
        for boundary in self.system.boundaries:
            if self.assumption_manager.should_skip_explicit_boundary(boundary.variable, self.system):
                continue
            try:
                index = registry.get_index(boundary.variable)
                variable = registry.get_record(boundary.variable)
            except KeyError as exc:
                raise KeyError(f"boundary references unknown variable: {exc}") from exc
            records.append(
                ResidualRecord(
                    name=f"boundary:{boundary.variable}",
                    value=float(x[index] - boundary.value),
                    scale=boundary.scale if boundary.scale is not None else variable.scale,
                    source="boundary",
                    role="boundary",
                    diagnostic_key="boundary_mismatch",
                    description=boundary.description,
                )
            )
        return records
