"""Real fixture objects for the finite scalar-snapshot contract."""
from pathlib import Path
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.schema.model_dataset_validation import ModelValidationPlanSpec

ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / 'examples/testfile_contracts/pump_loop'


def snapshot_inputs(audit, observed):
    return dict(
        plan=ModelValidationPlanSpec(validation_id='scalar-contract', audit_file='model/pump_loop_hierarchy.yaml',
                                     observed_file='observed/clean_observed.yaml'),
        base_dir=PUMP,
        audit_spec=load_hierarchical_audit_spec(PUMP / 'model/pump_loop_hierarchy.yaml') if audit else None,
        scalar_observed=load_observed_values(PUMP / 'observed/clean_observed.yaml') if observed else None,
        scalar_direct={'audit_pass': True})
