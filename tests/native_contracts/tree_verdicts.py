"""Direct tree verdicts contracts against production code."""
from ._audit_cases import EXPECTED_AUDIT, LABELS, ROOT, replay_case
from contextlib import contextmanager
PORT_VALUES = {'growth_coarse_bad_audit': 'FAIL', 'growth_planned_bad_audit': 'FAIL', 'hierarchy_evaluate_partial_tree_view_bad_audit': 'FAIL', 'hierarchy_evaluate_derived_child_bad_audit': 'PASS', 'hierarchy_evaluate_partial_tree_view_not_checked': 'not checked', 'observed_q_unmapped': 'PASS', 'observed_ai': 'PASS', 'observed_ai_half': 'no checks'}

REAL_CASE_IDS = ('growth_coarse_bad_audit', 'growth_planned_bad_audit', 'hierarchy_evaluate_partial_tree_view_bad_audit', 'hierarchy_evaluate_derived_child_bad_audit', 'hierarchy_evaluate_partial_tree_view_not_checked')


_CONSERVATION = 'Inspect sibling inflow/outflow, loss, storage, and boundary-condition variables before adding deeper component physics.'


HINT_ROWS = {'observed_q_unmapped': ('hint: conservation_balance heater.coolant_heat_balance, mix.flow_merge_temperature_balance: ' + _CONSERVATION, 'hint: unit_conversion heater.Q_dot_W multiply by 1000'), 'observed_ai': ('hint: conservation_balance mix.flow_merge_temperature_balance: ' + _CONSERVATION,)}


RESOLUTION_ROWS = {'observed_ai': ('mix.T_out_K +-0.2 K',), 'observed_ai_half': ('mix.T_out_K +-8 K (default scale)',)}


@contextmanager
def _rendered_lines():
    from physicsguard.core import tree_view
    original=tree_view.render_tree_view
    captured=[]
    def render(*args,**kwargs):
        text=original(*args,**kwargs);captured.extend(text.splitlines());return text
    tree_view.render_tree_view=render
    try:yield captured
    finally:tree_view.render_tree_view=original


def assert_native_contract():
    mismatches = []
    for key in REAL_CASE_IDS:
        with _rendered_lines() as lines:
            label, audit, ports, report, assumptions = replay_case(key)
        if key == 'hierarchy_evaluate_partial_tree_view_bad_audit' and (not lines or any(('components:' in line or line.startswith('links:') for line in lines))):
            mismatches.append('verdict_lines_omit_structure: verdict rows repeat declared structure')
        if label != LABELS[key]:
            mismatches.append(f'{key}: native label {label!r}, expected {LABELS[key]!r}')
        if audit is not None and audit != EXPECTED_AUDIT[key]:
            mismatches.append(f'{key}: audit_pass differs')
        if ports[2] != PORT_VALUES[key]:
            mismatches.append(f'{key}: native tree_verdict {ports[2]!r}, expected {PORT_VALUES[key]!r}')
    from physicsguard.core.hierarchy import HierarchicalAuditRunner, describe_hierarchy
    from physicsguard.core.tree_view import render_tree_view
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values
    shower = ROOT / 'examples/hierarchical/shower_mix'
    for case_id in tuple(dict.fromkeys((*HINT_ROWS, *RESOLUTION_ROWS))):
        case_mismatches = []
        audit_file = 'audit_default_scales.yaml' if case_id == 'observed_ai_half' else 'audit.yaml'
        spec = load_hierarchical_audit_spec(shower / audit_file)
        observed = load_observed_values(shower / (case_id + '.yaml'))
        runner = HierarchicalAuditRunner(spec, base_dir=shower)
        report = runner.to_dict(runner.evaluate_observed(observed))
        description = describe_hierarchy(spec, base_dir=shower)
        text = render_tree_view(description, report=report)
        rows = tuple((line for line in text.splitlines() if line.startswith('hint:')))
        root = next((row for row in report['block_verdicts'] if row['level'] == 0))
        native_port = ('PASS' if root['own_audit_pass'] else 'FAIL') if root['checked_residual_count'] else 'not checked' if root['missing_required_variables'] else 'no checks'
        if native_port != PORT_VALUES[case_id]:
            case_mismatches.append(f'native root port {native_port!r}, expected {PORT_VALUES[case_id]!r}')
        if case_id in HINT_ROWS and (rows != HINT_ROWS[case_id] or len(rows) != len(report['bug_family_followups'])):
            case_mismatches.append(f'hint_shown_in_tree: expected {HINT_ROWS[case_id]!r}, got {rows!r}')
        if case_id in RESOLUTION_ROWS:
            expected_value = 8.0 if case_id == 'observed_ai_half' else 0.2
            expected_default = case_id == 'observed_ai_half'
            resolution_lines = [line for line in text.splitlines() if line.startswith('resolution:')]
            fragment = RESOLUTION_ROWS[case_id][0]
            entry = report.get('resolution', {}).get('mix.T_out_K')
            if not any((fragment in line for line in resolution_lines)) or entry is None:
                case_mismatches.append(f'resolution_shown: missing native resolution {fragment!r}')
            elif abs(entry['value'] - expected_value) > expected_value * 0.0001 or entry['default_scale'] is not expected_default:
                case_mismatches.append(f'resolution_shown: wrong native sensitivity or scale origin: {entry!r}')
            owned = {component: block['id'] for block in description['blocks'] for component in block['component_ids']}
            checked = {row['block_id'] for row in report['block_verdicts'] if row['checked_residual_count']}
            expected_variables = {name for name in observed.variables if owned.get(name.split('.', 1)[0]) in checked}
            resolution = report.get('resolution', {})
            if set(resolution) != expected_variables:
                case_mismatches.append('resolution_shown: observed variables omitted or invented')
            visible = {part for line in resolution_lines for part in line.removeprefix('resolution: ').split(', ')}
            for name in expected_variables & resolution.keys():
                entry = resolution[name]
                if entry is None:
                    token = f'{name} unchecked'
                else:
                    token = f"{name} +-{entry['value']:.2g} {entry['unit']}".rstrip() + (' (scale source unavailable)' if entry['default_scale'] is None else ' (default scale)' if entry['default_scale'] else '')
                    if entry['unit'] != observed.variables[name].unit or entry['residual'] not in report['checked_residuals']:
                        case_mismatches.append(f'resolution_shown: wrong unit or unchecked residual for {name}')
                if token not in visible:
                    case_mismatches.append(f'resolution_shown: native line omits {token!r}')
        if case_mismatches:
            mismatches.append(f'{case_id}: ' + '; '.join(case_mismatches))
    assert not mismatches, mismatches

