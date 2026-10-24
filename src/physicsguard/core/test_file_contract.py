"""One executable CSV/TSV contract, preserving native freshness and analysis gates."""
from dataclasses import dataclass
from pathlib import Path
import csv
import math

from physicsguard.core.data_file_manifest import sha256_file, field_signature_hash
from physicsguard.core.parameter_coverage import (ContractFinding, ContractReview, _status, _next_actions,
                                                check_field_mappings, confidence_value, field_targets)
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.units import unit_conversion
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.test_file_contract_loader import load_test_file_contract, load_data_file_manifest
from physicsguard.schema.parameter_coverage import ParameterRoleMatrixSpec, RoleAssignmentSpec, MappingEdgeSpec


@dataclass(frozen=True)
class ResolvedArtifact:
    value: object
    path: Path


@dataclass(frozen=True)
class ResolvedTestFileContract:
    contract: object
    contract_path: Path
    manifest: ResolvedArtifact
    data_path: Path
    model_path: Path


def resolve_test_file_contract(path):
    path = Path(path).resolve()
    contract = load_test_file_contract(path)
    manifest_path = (path.parent / contract.manifest).resolve()
    return ResolvedTestFileContract(contract, path, ResolvedArtifact(load_data_file_manifest(manifest_path), manifest_path),
                                    (path.parent / contract.data_file).resolve(), (path.parent / contract.model).resolve())


def _manifest_findings(resolved):
    contract, manifest = resolved.contract, resolved.manifest.value
    findings = []
    def add(code, message, target=None):
        findings.append(ContractFinding('error', code, message, target=target))
    if not resolved.data_path.is_file():
        add('source_file_missing', 'data file is missing', str(resolved.data_path))
    elif not manifest.source_file.content_hash or sha256_file(resolved.data_path) != manifest.source_file.content_hash:
        add('source_file_hash_mismatch', 'manifest content hash does not match the data file')
    manifest_source = (resolved.manifest.path.parent / manifest.source_file.path).resolve()
    if manifest_source != resolved.data_path:
        add('manifest_source_path_mismatch', 'manifest identifies another file')
    if manifest.field_signature_hash != field_signature_hash(manifest):
        add('manifest_field_signature_mismatch', 'manifest field signature is absent or stale')
    if not manifest.extractor.script or not manifest.extractor.script_hash:
        add('manifest_missing_extractor_identity', 'manifest requires extractor identity and hash')
    generator = 'physicsguard.core.data_file_manifest.generate_delimited_manifest'
    if manifest.extractor.script == generator:
        from physicsguard.core.data_file_manifest import _self_script_hash
        if manifest.extractor.script_hash != _self_script_hash():
            add('extractor_script_hash_mismatch', 'manifest generator has changed; regenerate the manifest')
    extractor = contract.extractor
    if extractor:
        script = (resolved.contract_path.parent / extractor.script).resolve()
        if script.is_file():
            if sha256_file(script) != manifest.extractor.script_hash:
                add('extractor_script_hash_mismatch', 'extractor script differs from the manifest hash')
        elif extractor.script != manifest.extractor.script:
            add('extractor_script_missing', 'extractor script cannot be found')
        if extractor.script_hash and extractor.script_hash != manifest.extractor.script_hash:
            add('extractor_script_hash_mismatch', 'declared extractor hash differs from the manifest')
    return findings


def _model_target_units(resolved):
    from physicsguard.io.test_file_contract_loader import load_yaml_mapping
    from physicsguard.io.yaml_loader import load_system_spec
    data = load_yaml_mapping(resolved.model_path)
    system = load_hierarchical_audit_spec(resolved.model_path).system if 'system' in data else load_system_spec(resolved.model_path)
    registry = ResidualBuilder(system).build_registry()
    return {name: registry.get_record(name).unit for name in registry.names()}


def check_test_file_contract(path):
    resolved = resolve_test_file_contract(path)
    contract = resolved.contract
    findings = _manifest_findings(resolved)
    if not resolved.model_path.is_file():
        findings.append(ContractFinding('error', 'model_file_missing', 'model file is missing', target=str(resolved.model_path)))
        units = {}
    else:
        if contract.model_hash and sha256_file(resolved.model_path) != contract.model_hash:
            findings.append(ContractFinding('error', 'model_hash_mismatch', 'bound model hash is stale'))
        try:
            units = _model_target_units(resolved)
        except (ValueError, OSError, KeyError) as exc:
            units = {}
            findings.append(ContractFinding('error', 'model_load_failed', str(exc)))
    findings.extend(check_field_mappings(contract, resolved.manifest.value, units))
    if contract.time_column and contract.time_column not in {f.name for f in resolved.manifest.value.fields}:
        findings.append(ContractFinding('error', 'time_column_missing', 'declared time column is absent'))
    for segment in contract.segments:
        if segment.row_range and segment.row_range[1] >= (resolved.manifest.value.shape.row_count or 0):
            findings.append(ContractFinding('error', 'segment_out_of_range', 'segment rows exceed the data file', source_id=segment.segment_id))
    for defect in contract.known_defects:
        findings.append(ContractFinding('warning', 'known_file_defect', defect.description, source_id=defect.id,
                                        details={'impact': defect.impact, 'safe_claim': defect.safe_claim}))
    status = _status(findings)
    gate = {'pass':'open_for_scoped_analysis', 'partial':'limited_claims_only', 'fail':'blocked_until_contract_errors_are_fixed'}[status]
    return ContractReview('test_file_contract', status, status == 'pass', findings,
        dict(contract_id=contract.contract_id, file_id=contract.contract_id, manifest_field_count=len(resolved.manifest.value.fields),
             row_count=resolved.manifest.value.shape.row_count, field_count=len(contract.fields),
             error_count=sum(f.severity == 'error' for f in findings), warning_count=sum(f.severity == 'warning' for f in findings),
             analysis_claim_gate=gate, semantics='Identified, classified and mapped data permits scoped analysis, not proof of physical correctness.'),
        _next_actions(findings))


def inspect_test_file_contract(path):
    resolved = resolve_test_file_contract(path)
    return {'contract': resolved.contract.model_dump(mode='json', exclude_none=True),
            'manifest': resolved.manifest.value.model_dump(mode='json', exclude_none=True),
            'review': check_test_file_contract(path).to_dict()}


def contract_field_mappings(resolved):
    """Expose field declarations to validation; no old multi-file mapping input."""
    edges = []
    for name, field in resolved.contract.fields.items():
        if field.role not in {'measured', 'command'} or field.planned_child_model:
            continue
        for phase, target in field_targets(field).items():
            edges.append(MappingEdgeSpec(id=f'{name}:{phase}', source_id=f'field:{name}', relation='maps_to',
                target_type='physics_variable', target=target, confidence=max(0., confidence_value(field.confidence)),
                unit_evidence=field.unit if field.evidence else None, review_required=field.review_required,
                metadata={"row_offset": int(phase == "next_row")}))
    return edges


def contract_role_matrix(path):
    contract = load_test_file_contract(path)
    roles = []
    for name, field in contract.fields.items():
        roles.append(RoleAssignmentSpec(source_id=f'field:{name}', testbench_role='time' if name == contract.time_column else field.role or 'unknown',
            physical_role=field.role or 'unknown', model_role=field.target or 'field',
            coverage_status='excluded' if field.role == 'ignored' else 'review_required' if field.review_required else 'covered',
            reason=field.reason, measurement_confidence=max(0., confidence_value(field.confidence))))
    return ParameterRoleMatrixSpec(roles=roles)


def _read_ready_contract(path):
    review = check_test_file_contract(path)
    if not review.ok:
        raise ValueError('contract must pass before snapshot/series: ' + ', '.join(f.type for f in review.findings))
    resolved = resolve_test_file_contract(path)
    manifest = resolved.manifest.value
    with resolved.data_path.open(encoding=manifest.format.encoding, newline='') as stream:
        rows = [{key.strip() if isinstance(key, str) else key: value for key, value in row.items()}
                for row in csv.DictReader(stream, delimiter=manifest.format.delimiter or ',')]
    return resolved, rows, _model_target_units(resolved)


def _snapshot(resolved, rows, units, row):
    if row < 0 or row >= len(rows):
        raise ValueError(f'row {row} is outside the data file (zero-based)')
    variables = {}
    for name, field in resolved.contract.fields.items():
        if field.role not in {'measured', 'command'}:
            continue
        for phase, target in field_targets(field).items():
            index = row + (phase == 'next_row')
            if index >= len(rows):
                raise ValueError(f'{name}: row {row} needs next_row, which is outside the data file')
            factor, offset = unit_conversion(field.unit, units[target], field.conversion)
            try:
                number = float(rows[index][name]) * factor + offset
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f'{name}@{index}: expected a numeric observation') from exc
            if not math.isfinite(number):
                raise ValueError(f'{name}@{index}: observation must be finite')
            variables[target] = dict(value=number, unit=units[target], source=resolved.contract.data_file,
                external_signal=f'{name}@{index}', conversion_factor=factor, conversion_offset=offset,
                mapping_confidence=field.confidence, description=field.evidence)
    snapshot = dict(observation_name=f'{resolved.contract.contract_id}_step_{row}', variables=variables)
    if resolved.contract.source_model is not None:
        snapshot['source_model'] = resolved.contract.source_model.model_dump(mode='json', exclude_unset=True)
    return snapshot


def testfile_snapshot(path, row):
    resolved, rows, units = _read_ready_contract(path)
    return _snapshot(resolved, rows, units, row)


def testfile_series(path, row_range=None):
    resolved, rows, units = _read_ready_contract(path)
    needs_next = any('next_row' in field_targets(f) for f in resolved.contract.fields.values() if f.role in {'measured','command'})
    stop = len(rows) - int(needs_next)
    start = 0
    if row_range is not None:
        parts = row_range.split(':')
        if len(parts) != 2:
            raise ValueError('--rows must be A:B (zero-based, end exclusive)')
        start, stop = int(parts[0]), int(parts[1])
    if start < 0 or stop <= start or stop > len(rows) - int(needs_next):
        raise ValueError('invalid or empty row range')
    points = []
    for row in range(start, stop):
        point = dict(point_id=f'step_{row}', source_identity_id=resolved.contract.contract_id, source_row_index=row, variables=_snapshot(resolved, rows, units, row)['variables'])
        column = resolved.contract.time_column
        if column:
            raw = float(rows[row][column])
            time_field = resolved.contract.fields.get(column)
            factor, offset = unit_conversion(time_field.unit if time_field and time_field.unit else 's', 's')
            timestamp = raw*factor+offset
            if not math.isfinite(timestamp):
                raise ValueError(f'{column}@{row}: time must be finite')
            point['timestamp'] = timestamp
        points.append(point)
    result = dict(series_id=resolved.contract.contract_id, time_unit='s', points=points)
    if resolved.contract.source_model is not None:
        result['source_model'] = resolved.contract.source_model.model_dump(mode='json', exclude_unset=True)
    return result
