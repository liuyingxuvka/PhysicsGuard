"""Provider-neutral observation and bounded execution of FMI 3 packages."""

from __future__ import annotations

import ast
import ctypes
import _ctypes
import hashlib
import json
import platform
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree

import yaml
from pydantic import ValidationError

from physicsguard.schema.fmi_observation import (
    FMI_OBSERVATION_RESULT_SCHEMA,
    FmiArtifactObservation,
    FmiBehaviorCase,
    FmiBehaviorCaseResult,
    FmiMemberObservation,
    FmiObservationRequest,
    FmiObservationResult,
    FmiOracleDefinition,
    FmiSourceCensusMember,
    FmiVariableObservation,
    fingerprint_fmi_behavior_case_universe,
    fingerprint_fmi_source_census,
    fingerprint_fmi_observation_result,
    normalize_fmi_source_fragment,
)
from physicsguard.schema.physical_model_blueprint import (
    FmiVariableSemanticContract,
    ObservedNativeBehaviorCase,
    ObservedSemanticSelector,
    canonical_blueprint_fingerprint,
    fingerprint_native_behavior_case_universe_member,
    fingerprint_observed_semantic_selector,
)


FMI_STATUS_NAMES = {
    0: "ok",
    1: "warning",
    2: "discard",
    3: "error",
    4: "fatal",
    5: "pending",
}


class FmiObservationError(ValueError):
    """Visible current-contract loading or observation failure."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def load_fmi_observation_request(path: str | Path) -> FmiObservationRequest:
    """Load exactly the current FMI observation request schema."""

    request_path = Path(path)
    if request_path.suffix.lower() not in {".json", ".yaml", ".yml"}:
        raise FmiObservationError(
            "unsupported_fmi_observation_request_format",
            "FMI observation requests use only current JSON or YAML",
        )
    try:
        text = request_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FmiObservationError(
            "fmi_observation_request_read_error",
            f"failed to read FMI observation request: {exc.strerror or type(exc).__name__}",
        ) from exc
    try:
        payload = json.loads(text) if request_path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise FmiObservationError(
            "malformed_fmi_observation_request",
            f"malformed FMI observation request: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise FmiObservationError(
            "invalid_fmi_observation_request_root",
            "FMI observation request root must be an object",
        )
    try:
        return FmiObservationRequest.model_validate(payload)
    except ValidationError as exc:
        raise FmiObservationError(
            "invalid_fmi_observation_request",
            f"invalid current FMI observation request: {exc}",
        ) from exc


def review_fmi_observation_request(path: str | Path) -> FmiObservationResult:
    """Replay one exact request relative to its own declared artifact root."""

    request_path = Path(path)
    request = load_fmi_observation_request(request_path)
    return observe_fmi_observation_request(request, base_dir=request_path.parent)


def observe_fmi_observation_request(
    request: FmiObservationRequest,
    *,
    base_dir: Path,
) -> FmiObservationResult:
    """Verify frozen bytes/XML and execute declared standard FMI cases.

    No target name, revision, locator, hash, variable, or expected result is
    selected by this observer.  All such identities come from the strict
    request, and all returned locators remain forward-relative.
    """

    artifacts_by_id = {item.artifact_id: item for item in request.artifacts}
    artifact_paths = {
        artifact.artifact_id: base_dir / Path(*PurePosixPath(artifact.relative_path).parts)
        for artifact in request.artifacts
    }
    artifact_observations: list[FmiArtifactObservation] = []
    source_census: list[FmiSourceCensusMember] = []
    artifact_bytes: dict[str, bytes] = {}
    first_gap: str | None = None
    findings: list[str] = []
    behavior_case_universe: list[ObservedNativeBehaviorCase] = []
    for behavior_case in request.behavior_cases:
        case_payload: dict[str, Any] = {
            "native_case_id": behavior_case.case_id,
            "disposition": "required",
            "native_input_fingerprint": canonical_blueprint_fingerprint(
                behavior_case.model_dump(mode="json", exclude_none=True)
            ),
        }
        case_payload["member_fingerprint"] = fingerprint_native_behavior_case_universe_member(case_payload)
        behavior_case_universe.append(ObservedNativeBehaviorCase.model_validate(case_payload))

    for artifact in request.artifacts:
        path = artifact_paths[artifact.artifact_id]
        local_findings: list[str] = []
        actual_sha: str | None = None
        actual_size: int | None = None
        try:
            data = path.read_bytes()
        except OSError:
            local_findings.append("declared local artifact is unavailable")
        else:
            artifact_bytes[artifact.artifact_id] = data
            actual_size = len(data)
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != artifact.sha256:
                local_findings.append("artifact sha256 differs from the frozen expectation")
            if actual_size != artifact.size_bytes:
                local_findings.append("artifact byte count differs from the frozen expectation")
        if artifact.container_artifact_id is not None:
            container_path = artifact_paths[artifact.container_artifact_id]
            try:
                with zipfile.ZipFile(container_path) as archive:
                    member_bytes = _read_one_archive_member(
                        archive,
                        artifact.container_member_path or "",
                    )
            except (OSError, zipfile.BadZipFile, KeyError, FmiObservationError):
                local_findings.append("container member is unavailable or ambiguous")
            else:
                if actual_sha is None or hashlib.sha256(member_bytes).hexdigest() != actual_sha:
                    local_findings.append("local artifact differs from its frozen container member")
        status = "pass" if not local_findings else "blocked"
        if status != "pass" and first_gap is None:
            first_gap = "fmi_artifact_integrity_mismatch"
        artifact_observations.append(
            FmiArtifactObservation(
                artifact_id=artifact.artifact_id,
                role=artifact.role,
                relative_path=artifact.relative_path,
                expected_sha256=artifact.sha256,
                actual_sha256=actual_sha,
                expected_size_bytes=artifact.size_bytes,
                actual_size_bytes=actual_size,
                container_artifact_id=artifact.container_artifact_id,
                container_member_path=artifact.container_member_path,
                status=status,
                findings=local_findings,
            )
        )
        if actual_sha is not None:
            source_census.append(
                FmiSourceCensusMember(
                    source_member_id=f"fmi.artifact:{artifact.artifact_id}",
                    source_kind="artifact",
                    locator=artifact.relative_path,
                    role=artifact.role,
                    member_fingerprint=actual_sha,
                )
            )

    fmu_artifact = artifacts_by_id[request.fmu_artifact_id]
    fmu_path = artifact_paths[request.fmu_artifact_id]
    archive: zipfile.ZipFile | None = None
    archive_names: set[str] = set()
    model_root: ElementTree.Element | None = None
    model_description_bytes: bytes | None = None
    member_observations: list[FmiMemberObservation] = []
    variable_observations: list[FmiVariableObservation] = []
    behavior_results: list[FmiBehaviorCaseResult] = []
    fmi_version: str | None = None
    model_name: str | None = None
    model_identifier: str | None = None
    instantiation_token: str | None = None
    supported_interfaces: list[str] = []

    if request.fmu_artifact_id in artifact_bytes:
        try:
            archive = zipfile.ZipFile(fmu_path)
            archive_names = _validated_archive_names(archive)
        except (OSError, zipfile.BadZipFile, FmiObservationError) as exc:
            if first_gap is None:
                first_gap = "fmi_archive_invalid"
            findings.append(str(exc))
            archive = None

    if archive is not None:
        for archive_member in sorted(
            (item for item in archive.infolist() if not item.is_dir()),
            key=lambda item: PurePosixPath(item.filename.replace("\\", "/")).as_posix(),
        ):
            member_path = PurePosixPath(archive_member.filename.replace("\\", "/")).as_posix()
            member_bytes = _read_one_archive_member(archive, member_path)
            semantic_selectors = _observe_semantic_selectors_for_member(
                request,
                member_path=member_path,
                member_bytes=member_bytes,
            )
            unresolved_selectors = [item for item in semantic_selectors if item.status != "verified"]
            if unresolved_selectors:
                findings.extend(
                    f"semantic selector {item.selector_id!r} is unresolved in {member_path!r}"
                    for item in unresolved_selectors
                )
                if first_gap is None:
                    first_gap = "fmi_semantic_selector_unresolved"
            source_census.append(
                FmiSourceCensusMember(
                    source_member_id=f"fmi.member:{member_path}",
                    source_kind="archive_member",
                    locator=member_path,
                    role=_infer_fmi_member_role(member_path),
                    member_fingerprint=hashlib.sha256(member_bytes).hexdigest(),
                    semantic_selectors=semantic_selectors,
                )
            )
        for expected in request.expected_members:
            local_findings: list[str] = []
            actual_sha: str | None = None
            actual_size: int | None = None
            try:
                data = _read_one_archive_member(archive, expected.member_path)
            except (KeyError, FmiObservationError):
                local_findings.append("declared FMU member is unavailable or ambiguous")
            else:
                actual_size = len(data)
                actual_sha = hashlib.sha256(data).hexdigest()
                if actual_sha != expected.sha256:
                    local_findings.append("FMU member sha256 differs from the frozen expectation")
                if actual_size != expected.size_bytes:
                    local_findings.append("FMU member byte count differs from the frozen expectation")
                if expected.member_path == "modelDescription.xml":
                    model_description_bytes = data
            status = "pass" if not local_findings else "blocked"
            if status != "pass" and first_gap is None:
                first_gap = "fmi_member_integrity_mismatch"
            member_observations.append(
                FmiMemberObservation(
                    member_id=expected.member_id,
                    role=expected.role,
                    member_path=expected.member_path,
                    expected_sha256=expected.sha256,
                    actual_sha256=actual_sha,
                    expected_size_bytes=expected.size_bytes,
                    actual_size_bytes=actual_size,
                    status=status,
                    findings=local_findings,
                )
            )
        if model_description_bytes is None and "modelDescription.xml" in archive_names:
            model_description_bytes = _read_one_archive_member(archive, "modelDescription.xml")

    if model_description_bytes is None:
        if first_gap is None:
            first_gap = "fmi_model_description_missing"
    else:
        try:
            model_root = ElementTree.fromstring(model_description_bytes)
        except ElementTree.ParseError:
            if first_gap is None:
                first_gap = "fmi_model_description_malformed"
        else:
            fmi_version = model_root.attrib.get("fmiVersion")
            model_name = model_root.attrib.get("modelName")
            instantiation_token = model_root.attrib.get("instantiationToken") or model_root.attrib.get("guid")
            interfaces = {
                _local_name(child.tag): child
                for child in model_root
                if _local_name(child.tag) in {"ModelExchange", "CoSimulation", "ScheduledExecution"}
            }
            supported_interfaces = sorted(_snake_case(item) for item in interfaces)
            selected_interface = interfaces.get("ModelExchange")
            if selected_interface is not None:
                model_identifier = selected_interface.attrib.get("modelIdentifier")
            identity_mismatches = []
            if fmi_version != request.fmi_version:
                identity_mismatches.append("FMI version differs")
            if model_name != request.expected_model_name:
                identity_mismatches.append("model name differs")
            if model_identifier != request.expected_model_identifier:
                identity_mismatches.append("model identifier differs")
            if "model_exchange" not in supported_interfaces:
                identity_mismatches.append("declared Model Exchange interface is unavailable")
            if identity_mismatches:
                findings.extend(identity_mismatches)
                if first_gap is None:
                    first_gap = "fmi_model_identity_mismatch"

            actual_variables = _parse_variables(model_root)
            expected_variables_by_name = {
                item.variable_name: item for item in request.expected_variables
            }
            for variable_name, actual in sorted(actual_variables.items()):
                expected_variable = expected_variables_by_name.get(variable_name)
                typed_contract = None
                if (
                    expected_variable is not None
                    and expected_variable.physical_quantity_id is not None
                    and expected_variable.source_state_role is not None
                ):
                    typed_contract = FmiVariableSemanticContract(
                        variable_name=actual["variable_name"],
                        value_reference=actual["value_reference"],
                        variable_type=actual["variable_type"],
                        causality=actual["causality"],
                        variability=actual["variability"],
                        unit=actual["unit"],
                        derivative_of_value_reference=actual["derivative_of_value_reference"],
                        reinit=actual["reinit"],
                        physical_quantity_id=expected_variable.physical_quantity_id,
                        source_state_role=expected_variable.source_state_role,
                    )
                source_census.append(
                    FmiSourceCensusMember(
                        source_member_id=f"fmi.variable:{variable_name}",
                        source_kind="variable",
                        locator=f"modelDescription.xml#variable:{variable_name}",
                        role=f"{actual.get('causality', 'unknown')}:{actual.get('variability', 'unknown')}",
                        member_fingerprint=canonical_blueprint_fingerprint(actual),
                        fmi_variable_contract=typed_contract,
                    )
                )
            for expected in request.expected_variables:
                actual = actual_variables.get(expected.variable_name)
                local_findings: list[str] = []
                if actual is None:
                    local_findings.append("declared variable is absent from modelDescription.xml")
                    observed = {
                        "variable_name": expected.variable_name,
                        "value_reference": expected.value_reference,
                        "variable_type": expected.variable_type,
                        "causality": expected.causality,
                        "variability": expected.variability,
                        "unit": expected.unit,
                        "start": expected.start,
                        "minimum": expected.minimum,
                        "maximum": expected.maximum,
                        "derivative_of_value_reference": expected.derivative_of_value_reference,
                        "reinit": expected.reinit,
                    }
                else:
                    observed = actual
                    for field_name in (
                        "value_reference",
                        "variable_type",
                        "causality",
                        "variability",
                        "unit",
                        "start",
                        "minimum",
                        "maximum",
                        "derivative_of_value_reference",
                        "reinit",
                    ):
                        if observed.get(field_name) != getattr(expected, field_name):
                            local_findings.append(f"{field_name} differs from the frozen expectation")
                status = "pass" if not local_findings else "blocked"
                if status != "pass" and first_gap is None:
                    first_gap = "fmi_variable_contract_mismatch"
                variable_observations.append(
                    FmiVariableObservation(
                        **observed,
                        status=status,
                        findings=local_findings,
                    )
                )

            oracle_expectation_findings = _review_declared_oracle_expectations(
                request,
                actual_variables,
            )
            if oracle_expectation_findings:
                findings.extend(oracle_expectation_findings)
                if first_gap is None:
                    first_gap = "fmi_oracle_expectation_mismatch"

            expected_members_by_id = {item.member_id: item for item in request.expected_members}
            for oracle in request.oracles:
                source_paths = [
                    expected_members_by_id[member_id].member_path
                    for member_id in oracle.source_member_ids
                ]
                if not all(path in archive_names for path in source_paths):
                    continue
                for expression in oracle.expressions:
                    semantic_payload = {
                        "oracle_id": oracle.oracle_id,
                        "result_name": expression.result_name,
                        "expression": expression.expression,
                        "source_member_paths": source_paths,
                    }
                    source_census.append(
                        FmiSourceCensusMember(
                            source_member_id=(
                                f"fmi.semantic:{oracle.oracle_id}:{expression.result_name}"
                            ),
                            source_kind="semantic_fact",
                            locator=f"oracle:{oracle.oracle_id}/{expression.result_name}",
                            role="restricted_source_independent_oracle",
                            member_fingerprint=canonical_blueprint_fingerprint(semantic_payload),
                            semantic_expression=expression.expression,
                        )
                    )

            if request.behavior_cases:
                if archive is None or model_identifier is None or instantiation_token is None:
                    if first_gap is None:
                        first_gap = "fmi_execution_interface_unavailable"
                else:
                    behavior_results = _execute_behavior_cases(
                        archive,
                        archive_names,
                        request,
                        model_identifier=model_identifier,
                        instantiation_token=instantiation_token,
                        variables=actual_variables,
                    )
                    if any(item.status != "pass" for item in behavior_results) and first_gap is None:
                        first_gap = "fmi_behavior_case_failed"

    for case_result in behavior_results:
        source_census.append(
            FmiSourceCensusMember(
                source_member_id=f"fmi.case:{case_result.case_id}",
                source_kind="native_case",
                locator=f"native-case:{case_result.case_id}",
                role=case_result.operation,
                member_fingerprint=canonical_blueprint_fingerprint(
                    case_result.model_dump(mode="json", exclude_none=True)
                ),
            )
        )

    if archive is not None:
        archive.close()

    all_observations = [
        *(item.status for item in artifact_observations),
        *(item.status for item in member_observations),
        *(item.status for item in variable_observations),
        *(item.status for item in behavior_results),
    ]
    if first_gap is None and all(item == "pass" for item in all_observations):
        status = "pass"
    else:
        status = "blocked"
        first_gap = first_gap or "fmi_observation_incomplete"

    payload: dict[str, Any] = {
        "schema_version": FMI_OBSERVATION_RESULT_SCHEMA,
        "observation_id": request.observation_id,
        "target_system_id": request.target_system_id,
        "subject_revision": request.subject_revision,
        "request_fingerprint": request.request_fingerprint,
        "source": request.source.model_dump(mode="json", exclude_none=False),
        "fmi_version": fmi_version,
        "model_name": model_name,
        "model_identifier": model_identifier,
        "instantiation_token": instantiation_token,
        "supported_interface_kinds": supported_interfaces,
        "artifact_observations": [item.model_dump(mode="json", exclude_none=False) for item in artifact_observations],
        "member_observations": [item.model_dump(mode="json", exclude_none=False) for item in member_observations],
        "variable_observations": [item.model_dump(mode="json", exclude_none=False) for item in variable_observations],
        "behavior_case_results": [item.model_dump(mode="json", exclude_none=False) for item in behavior_results],
        "behavior_case_universe": [
            item.model_dump(mode="json", exclude_none=False) for item in behavior_case_universe
        ],
        "behavior_case_universe_fingerprint": (
            fingerprint_fmi_behavior_case_universe(behavior_case_universe)
            if behavior_case_universe
            else None
        ),
        "source_census": [
            item.model_dump(mode="json", exclude_none=False)
            for item in sorted(source_census, key=lambda member: member.source_member_id)
        ],
        "source_census_fingerprint": fingerprint_fmi_source_census(source_census),
        "status": status,
        "first_gap_code": first_gap,
        "findings": findings,
        "safe_claim": (
            "The exact supplied FMI bytes, complete observable FMU member/XML-variable census, declared XML interface contract, "
            "and declared standard-interface cases were reproduced."
            if status == "pass"
            else "The supplied FMI observation remains non-pass at the first reported gap."
        ),
        "claim_boundary": (
            f"{request.source.claim_boundary} Exact local-byte agreement does not independently authenticate the remote publisher, "
            "prove the physical equations true, or establish empirical equivalence."
        ),
    }
    payload["result_fingerprint"] = fingerprint_fmi_observation_result(payload)
    return FmiObservationResult.model_validate(payload)


def _observe_semantic_selectors_for_member(
    request: FmiObservationRequest,
    *,
    member_path: str,
    member_bytes: bytes,
) -> list[ObservedSemanticSelector]:
    expected_members_by_id = {item.member_id: item for item in request.expected_members}
    applicable = [
        item
        for item in request.semantic_selectors
        if expected_members_by_id[item.source_member_id].member_path == member_path
    ]
    if not applicable:
        return []
    try:
        source_text = member_bytes.decode("utf-8")
    except UnicodeDecodeError:
        source_text = ""
    observed: list[ObservedSemanticSelector] = []
    for expectation in applicable:
        normalized_fragment = normalize_fmi_source_fragment(expectation.source_fragment)
        function_body = _extract_unique_c_function(source_text, expectation.function_name)
        gap_code: str | None = None
        if function_body is None:
            gap_code = "fmi_semantic_selector_function_unresolved"
        elif normalize_fmi_source_fragment(function_body).count(normalized_fragment) != 1:
            gap_code = "fmi_semantic_selector_fragment_unresolved"
        selector_payload: dict[str, Any] = {
            "selector_id": expectation.selector_id,
            "function_name": expectation.function_name,
            "normalized_source_fragment": normalized_fragment,
            "source_fragment_fingerprint": canonical_blueprint_fingerprint(normalized_fragment),
            "semantic_kind": expectation.semantic_kind,
            "semantic_statement": expectation.semantic_statement,
            "semantic_expression": expectation.semantic_expression,
            "status": "verified" if gap_code is None else "unresolved",
            "claim_boundary": expectation.claim_boundary,
            "first_gap_code": gap_code,
        }
        selector_payload["selector_fingerprint"] = fingerprint_observed_semantic_selector(selector_payload)
        observed.append(ObservedSemanticSelector.model_validate(selector_payload))
    return observed


def _extract_unique_c_function(source_text: str, function_name: str) -> str | None:
    if not source_text:
        return None
    pattern = re.compile(
        rf"\b{re.escape(function_name)}\s*\([^;{{}}]*\)\s*\{{",
        re.DOTALL,
    )
    matches = list(pattern.finditer(source_text))
    if len(matches) != 1:
        return None
    opening = source_text.find("{", matches[0].start(), matches[0].end())
    if opening < 0:
        return None
    depth = 0
    for index in range(opening, len(source_text)):
        character = source_text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source_text[matches[0].start() : index + 1]
    return None


def _read_one_archive_member(archive: zipfile.ZipFile, member_path: str) -> bytes:
    normalized = PurePosixPath(member_path.replace("\\", "/")).as_posix()
    matches = [item for item in archive.infolist() if PurePosixPath(item.filename.replace("\\", "/")).as_posix() == normalized]
    if len(matches) != 1 or matches[0].is_dir():
        raise FmiObservationError(
            "fmi_archive_member_ambiguous",
            f"archive member {normalized!r} is missing, duplicated, or not a file",
        )
    return archive.read(matches[0])


def _validated_archive_names(archive: zipfile.ZipFile) -> set[str]:
    normalized: list[str] = []
    for member in archive.infolist():
        path = PurePosixPath(member.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
            raise FmiObservationError(
                "unsafe_fmi_archive_member",
                "FMU contains an absolute or parent-traversing member",
            )
        normalized.append(path.as_posix())
    if len(normalized) != len(set(normalized)):
        raise FmiObservationError(
            "duplicate_fmi_archive_member",
            "FMU contains duplicate normalized member names",
        )
    return set(normalized)


def _infer_fmi_member_role(member_path: str) -> str:
    lowered = member_path.lower()
    if lowered == "modeldescription.xml":
        return "model_description"
    if lowered.startswith("sources/"):
        return "source"
    if lowered.startswith("binaries/"):
        return "binary"
    if lowered.startswith("documentation/"):
        return "documentation"
    if lowered.startswith("resources/"):
        return "resource"
    if lowered.endswith((".csv", ".svg", ".png", ".jpg", ".jpeg")):
        return "result"
    return "other"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _snake_case(value: str) -> str:
    result = []
    for index, character in enumerate(value):
        if character.isupper() and index:
            result.append("_")
        result.append(character.lower())
    return "".join(result)


def _optional_float(value: str | None) -> float | None:
    return None if value is None else float(value)


def _optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.lower() == "true"


def _parse_variables(root: ElementTree.Element) -> dict[str, dict[str, Any]]:
    declared_types: dict[str, dict[str, str]] = {}
    type_definitions = next((item for item in root if _local_name(item.tag) == "TypeDefinitions"), None)
    if type_definitions is not None:
        for declared_type in type_definitions:
            type_name = declared_type.attrib.get("name")
            if type_name:
                declared_types[type_name] = dict(declared_type.attrib)
    model_variables = next((item for item in root if _local_name(item.tag) == "ModelVariables"), None)
    if model_variables is None:
        return {}
    variables: dict[str, dict[str, Any]] = {}
    for variable in model_variables:
        name = variable.attrib.get("name")
        value_reference = variable.attrib.get("valueReference")
        if not name or value_reference is None:
            continue
        inherited = declared_types.get(variable.attrib.get("declaredType", ""), {})
        value = {
            "variable_name": name,
            "value_reference": int(value_reference),
            "variable_type": _local_name(variable.tag),
            "causality": variable.attrib.get("causality", "local"),
            "variability": variable.attrib.get("variability", "continuous"),
            "unit": variable.attrib.get("unit", inherited.get("unit")),
            "start": _optional_float(variable.attrib.get("start", inherited.get("start"))),
            "minimum": _optional_float(variable.attrib.get("min", inherited.get("min"))),
            "maximum": _optional_float(variable.attrib.get("max", inherited.get("max"))),
            "derivative_of_value_reference": (
                int(variable.attrib["derivative"]) if "derivative" in variable.attrib else None
            ),
            "reinit": _optional_bool(variable.attrib.get("reinit")),
        }
        variables[name] = value
    return variables


def _platform_binary_location(model_identifier: str) -> tuple[str, str]:
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        architecture = "x86_64"
    elif machine in {"arm64", "aarch64"}:
        architecture = "aarch64"
    elif machine in {"x86", "i386", "i686"}:
        architecture = "x86"
    else:
        architecture = machine
    if sys.platform == "win32":
        return f"binaries/{architecture}-windows/{model_identifier}.dll", ".dll"
    if sys.platform.startswith("linux"):
        return f"binaries/{architecture}-linux/{model_identifier}.so", ".so"
    if sys.platform == "darwin":
        return f"binaries/{architecture}-darwin/{model_identifier}.dylib", ".dylib"
    return "", ""


def _execute_behavior_cases(
    archive: zipfile.ZipFile,
    archive_names: set[str],
    request: FmiObservationRequest,
    *,
    model_identifier: str,
    instantiation_token: str,
    variables: dict[str, dict[str, Any]],
) -> list[FmiBehaviorCaseResult]:
    binary_member, _ = _platform_binary_location(model_identifier)
    if not binary_member or binary_member not in archive_names:
        return [
            FmiBehaviorCaseResult(
                case_id=case.case_id,
                operation=case.operation,
                independent_oracle_id=case.independent_oracle_id,
                terminal_status="fatal",
                oracle_values={},
                observed_values={},
                status="blocked",
                findings=["the current platform FMI binary is not present in the supplied FMU"],
            )
            for case in request.behavior_cases
        ]
    with tempfile.TemporaryDirectory(prefix="physicsguard-fmi-") as temporary_directory:
        extraction_root = Path(temporary_directory)
        archive.extractall(extraction_root)
        library_path = extraction_root / Path(*PurePosixPath(binary_member).parts)
        try:
            library = ctypes.CDLL(str(library_path))
        except OSError:
            return [
                FmiBehaviorCaseResult(
                    case_id=case.case_id,
                    operation=case.operation,
                    independent_oracle_id=case.independent_oracle_id,
                    terminal_status="fatal",
                    oracle_values={},
                    observed_values={},
                    status="blocked",
                    findings=["the current platform FMI binary could not be loaded"],
                )
                for case in request.behavior_cases
            ]
        handle = library._handle
        try:
            try:
                _configure_fmi3_functions(library)
            except AttributeError:
                return [
                    FmiBehaviorCaseResult(
                        case_id=case.case_id,
                        operation=case.operation,
                        independent_oracle_id=case.independent_oracle_id,
                        terminal_status="fatal",
                        oracle_values={},
                        observed_values={},
                        status="blocked",
                        findings=["the FMI binary does not expose the required FMI 3 Model Exchange functions"],
                    )
                    for case in request.behavior_cases
                ]
            resource_path = (extraction_root / "resources").resolve().as_uri()
            oracles = {item.oracle_id: item for item in request.oracles}
            return [
                _execute_one_case(
                    library,
                    case,
                    variables=variables,
                    oracle=oracles[case.independent_oracle_id],
                    instantiation_token=instantiation_token,
                    resource_path=resource_path,
                )
                for case in request.behavior_cases
            ]
        finally:
            if sys.platform == "win32":
                _ctypes.FreeLibrary(handle)
            else:
                _ctypes.dlclose(handle)
            del library


def _configure_fmi3_functions(library: ctypes.CDLL) -> None:
    void_pointer = ctypes.c_void_p
    library.fmi3InstantiateModelExchange.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_uint8,
        ctypes.c_uint8,
        void_pointer,
        void_pointer,
    ]
    library.fmi3InstantiateModelExchange.restype = void_pointer
    library.fmi3EnterInitializationMode.argtypes = [
        void_pointer,
        ctypes.c_uint8,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_uint8,
        ctypes.c_double,
    ]
    library.fmi3EnterInitializationMode.restype = ctypes.c_int
    library.fmi3ExitInitializationMode.argtypes = [void_pointer]
    library.fmi3ExitInitializationMode.restype = ctypes.c_int
    library.fmi3EnterContinuousTimeMode.argtypes = [void_pointer]
    library.fmi3EnterContinuousTimeMode.restype = ctypes.c_int
    library.fmi3SetFloat64.argtypes = [
        void_pointer,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
    ]
    library.fmi3SetFloat64.restype = ctypes.c_int
    library.fmi3GetFloat64.argtypes = [
        void_pointer,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
    ]
    library.fmi3GetFloat64.restype = ctypes.c_int
    library.fmi3UpdateDiscreteStates.argtypes = [
        void_pointer,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_double),
    ]
    library.fmi3UpdateDiscreteStates.restype = ctypes.c_int
    library.fmi3FreeInstance.argtypes = [void_pointer]
    library.fmi3FreeInstance.restype = None


def _execute_one_case(
    library: ctypes.CDLL,
    case: FmiBehaviorCase,
    *,
    variables: dict[str, dict[str, Any]],
    oracle: FmiOracleDefinition,
    instantiation_token: str,
    resource_path: str,
) -> FmiBehaviorCaseResult:
    instance = library.fmi3InstantiateModelExchange(
        f"physicsguard_{case.case_id}".encode("utf-8"),
        instantiation_token.encode("utf-8"),
        resource_path.encode("utf-8"),
        0,
        0,
        None,
        None,
    )
    if not instance:
        return FmiBehaviorCaseResult(
            case_id=case.case_id,
            operation=case.operation,
            independent_oracle_id=case.independent_oracle_id,
            terminal_status="fatal",
            oracle_values={},
            observed_values={},
            status="blocked",
            findings=["fmi3InstantiateModelExchange returned no instance"],
        )
    findings: list[str] = []
    observed_values: dict[str, float] = {}
    oracle_values, oracle_findings = _derive_case_oracle_values(case, oracle, variables)
    findings.extend(oracle_findings)
    terminal_code = 4
    try:
        terminal_code = int(library.fmi3EnterInitializationMode(instance, 0, 0.0, case.start_time, 0, 0.0))
        if terminal_code <= 1 and case.assignments:
            terminal_code = _set_float64(library, instance, case.assignments, variables)
        if case.operation != "rejected_set" and terminal_code <= 1:
            terminal_code = int(library.fmi3ExitInitializationMode(instance))
        if case.operation == "event_update" and terminal_code <= 1:
            terminal_code = _update_discrete_states(library, instance)
        if case.operation == "read_after_initialization" and terminal_code <= 1:
            terminal_code = int(library.fmi3EnterContinuousTimeMode(instance))
        if case.operation != "rejected_set" and terminal_code <= 1 and case.read_variable_names:
            terminal_code, observed_values = _get_float64(
                library,
                instance,
                case.read_variable_names,
                variables,
            )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        terminal_code = 4
        findings.append(f"standard FMI case execution failed: {type(exc).__name__}")
    finally:
        library.fmi3FreeInstance(instance)

    terminal_status = FMI_STATUS_NAMES.get(terminal_code, "fatal")
    if terminal_status != case.expected_terminal_status:
        findings.append(
            f"terminal status {terminal_status!r} differs from expected {case.expected_terminal_status!r}"
        )
    for expected in case.expected_values:
        actual = observed_values.get(expected.variable_name)
        if actual is None:
            findings.append(f"expected variable {expected.variable_name!r} was not observed")
        elif abs(actual - expected.value) > expected.absolute_tolerance:
            findings.append(
                f"variable {expected.variable_name!r} differs from its independent expected value"
            )
        oracle_value = oracle_values.get(expected.variable_name)
        if oracle_value is None:
            findings.append(f"independent oracle did not derive {expected.variable_name!r}")
        else:
            if abs(expected.value - oracle_value) > expected.absolute_tolerance:
                findings.append(
                    f"caller expected value for {expected.variable_name!r} differs from the restricted independent oracle"
                )
            if actual is not None and abs(actual - oracle_value) > expected.absolute_tolerance:
                findings.append(
                    f"observed value for {expected.variable_name!r} differs from the restricted independent oracle"
                )
    return FmiBehaviorCaseResult(
        case_id=case.case_id,
        operation=case.operation,
        independent_oracle_id=case.independent_oracle_id,
        terminal_status=terminal_status,
        oracle_values=oracle_values,
        observed_values=observed_values,
        status="pass" if not findings else "blocked",
        findings=findings,
    )


def _derive_case_oracle_values(
    case: FmiBehaviorCase,
    oracle: FmiOracleDefinition,
    variables: dict[str, dict[str, Any]],
) -> tuple[dict[str, float], list[str]]:
    assignments = {item.variable_name: item.value for item in case.assignments}
    environment: dict[str, float | bool] = {}
    findings: list[str] = []
    for expression_name, variable_name in case.oracle_input_bindings.items():
        value = assignments.get(variable_name)
        if value is None:
            variable = variables.get(variable_name)
            value = variable.get("start") if variable is not None else None
        if value is None:
            findings.append(
                f"independent oracle input {expression_name!r} has no assigned or XML start value"
            )
        else:
            environment[expression_name] = float(value)
    result_values: dict[str, float] = {}
    for expression in oracle.expressions:
        try:
            value = _evaluate_restricted_oracle_expression(expression.expression, environment)
        except (SyntaxError, TypeError, ValueError, KeyError, ZeroDivisionError) as exc:
            findings.append(
                f"restricted independent oracle expression {expression.result_name!r} failed: {type(exc).__name__}"
            )
            continue
        if isinstance(value, bool):
            numeric = 1.0 if value else 0.0
        else:
            numeric = float(value)
        if not (numeric == numeric and abs(numeric) != float("inf")):
            findings.append(
                f"restricted independent oracle expression {expression.result_name!r} returned a non-finite value"
            )
            continue
        environment[expression.result_name] = numeric
        result_values[expression.result_name] = numeric
    oracle_values = {
        variable_name: result_values[result_name]
        for variable_name, result_name in case.oracle_output_bindings.items()
        if result_name in result_values
    }
    return oracle_values, findings


def _review_declared_oracle_expectations(
    request: FmiObservationRequest,
    variables: dict[str, dict[str, Any]],
) -> list[str]:
    oracles = {item.oracle_id: item for item in request.oracles}
    findings: list[str] = []
    for case in request.behavior_cases:
        oracle_values, oracle_findings = _derive_case_oracle_values(
            case,
            oracles[case.independent_oracle_id],
            variables,
        )
        findings.extend(f"case {case.case_id!r}: {finding}" for finding in oracle_findings)
        for expected in case.expected_values:
            oracle_value = oracle_values.get(expected.variable_name)
            if oracle_value is None:
                findings.append(
                    f"case {case.case_id!r}: independent oracle did not derive {expected.variable_name!r}"
                )
            elif abs(expected.value - oracle_value) > expected.absolute_tolerance:
                findings.append(
                    f"case {case.case_id!r}: caller expected value for {expected.variable_name!r} differs from the restricted independent oracle"
                )
    return findings


def _evaluate_restricted_oracle_expression(
    expression: str,
    environment: dict[str, float | bool],
) -> float | bool:
    tree = ast.parse(expression, mode="eval")

    def evaluate(node: ast.AST) -> float | bool:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool)):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in environment:
                raise KeyError(node.id)
            return environment[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return +value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            return left**right
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left = evaluate(node.left)
            right = evaluate(node.comparators[0])
            operation = node.ops[0]
            if isinstance(operation, ast.Lt):
                return left < right
            if isinstance(operation, ast.LtE):
                return left <= right
            if isinstance(operation, ast.Gt):
                return left > right
            if isinstance(operation, ast.GtE):
                return left >= right
            if isinstance(operation, ast.Eq):
                return left == right
            if isinstance(operation, ast.NotEq):
                return left != right
        if isinstance(node, ast.IfExp):
            return evaluate(node.body) if bool(evaluate(node.test)) else evaluate(node.orelse)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            values = [bool(evaluate(item)) for item in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        raise ValueError(f"unsupported restricted oracle syntax: {type(node).__name__}")

    return evaluate(tree)


def _set_float64(
    library: ctypes.CDLL,
    instance: ctypes.c_void_p,
    assignments,
    variables: dict[str, dict[str, Any]],
) -> int:
    references = []
    values = []
    for assignment in assignments:
        variable = variables[assignment.variable_name]
        if variable["variable_type"] != "Float64":
            raise TypeError("declared assignment is not Float64")
        references.append(variable["value_reference"])
        values.append(assignment.value)
    reference_array = (ctypes.c_uint32 * len(references))(*references)
    value_array = (ctypes.c_double * len(values))(*values)
    return int(
        library.fmi3SetFloat64(
            instance,
            reference_array,
            len(references),
            value_array,
            len(values),
        )
    )


def _get_float64(
    library: ctypes.CDLL,
    instance: ctypes.c_void_p,
    variable_names: list[str],
    variables: dict[str, dict[str, Any]],
) -> tuple[int, dict[str, float]]:
    references = []
    for name in variable_names:
        variable = variables[name]
        if variable["variable_type"] != "Float64":
            raise TypeError("declared read is not Float64")
        references.append(variable["value_reference"])
    reference_array = (ctypes.c_uint32 * len(references))(*references)
    value_array = (ctypes.c_double * len(references))()
    status = int(
        library.fmi3GetFloat64(
            instance,
            reference_array,
            len(references),
            value_array,
            len(references),
        )
    )
    return status, {name: float(value_array[index]) for index, name in enumerate(variable_names)}


def _update_discrete_states(library: ctypes.CDLL, instance: ctypes.c_void_p) -> int:
    discrete_states_need_update = ctypes.c_uint8()
    terminate_simulation = ctypes.c_uint8()
    nominals_changed = ctypes.c_uint8()
    values_changed = ctypes.c_uint8()
    next_event_time_defined = ctypes.c_uint8()
    next_event_time = ctypes.c_double()
    return int(
        library.fmi3UpdateDiscreteStates(
            instance,
            ctypes.byref(discrete_states_need_update),
            ctypes.byref(terminate_simulation),
            ctypes.byref(nominals_changed),
            ctypes.byref(values_changed),
            ctypes.byref(next_event_time_defined),
            ctypes.byref(next_event_time),
        )
    )


__all__ = [
    "FmiObservationError",
    "load_fmi_observation_request",
    "observe_fmi_observation_request",
    "review_fmi_observation_request",
]
