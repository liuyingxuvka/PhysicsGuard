# DataBank Contracts

All DataBank records should be plain JSON or YAML. Keep machine keys canonical
and language-neutral; localized display belongs in views, not contracts.

## Provider Closure Envelope

Each downstream Guard result must include:

```yaml
status: pass|partial|blocked
evidence: []
missing_inputs: []
stale_evidence: []
skipped_checks: []
safe_claim: ""
unsafe_claim_boundary: ""
next_actions: []
```

`databank_closure_check.py` blocks or downgrades broad claims when provider
results are missing required fields, stale, skipped, partial beyond scope, or
blocked.

Run `databank_contract_check.py` before relying on any contract file for closure
or navigation claims. Use `--check-paths --base DATABASE_ROOT` when the claim
depends on local file availability. A field that exists but is empty, malformed,
or impossible to resolve is not valid evidence.

## Database Root Contract

A DataBank root must be explicit. The expected layout is:

- `DATABASE_README.md`
- `DATABASE_STATUS.md`
- `databank_policy.json`
- `database_catalog.json`
- `database_history.jsonl`
- `contracts/`
- `projects/`
- `provider_results/`
- `navigation/`
- `closure_reports/`
- `queries/`

`database_history.jsonl` is append-only. Lifecycle transitions must be written
through `databank_lifecycle.py` or another tool that preserves a history event.

## Source Contract

Required fields:

- `id`
- `path`
- `sha256`
- `source_type`
- `read_only`
- `provenance`

Use for source files, reports, drawings, metadata tables, and external evidence
snapshots.

`sha256` must be a 64-character hex digest. When path checking is enabled,
`path` must resolve under the provided database base or be absolute.

## Data Contract

Required fields:

- `id`
- `path`
- `sha256`
- `row_count`
- `fields`
- `time_range`
- `units`
- `parameter_roles`

Use for test data and structured data manifests. Store metadata and hashes, not
raw large data copies.

## Model Contract

Required fields:

- `id`
- `path`
- `model_hash`
- `model_targets`
- `inputs`
- `outputs`
- `parent_model`
- `child_models`

Use for physical, logical, process, or timeline models whose current hash affects
validation freshness.

## Binding Contract

Required fields:

- `field_id`
- `model_target`
- `evidence`
- `confidence`
- `review_state`
- `unit_evidence`

Bindings are provider-owned. DataBank stores pointers and freshness state.

## Logic Contract

Required fields:

- `claim_id`
- `claim_text`
- `supporting_evidence`
- `assumptions`
- `limitations`
- `unsafe_claim_boundary`

Use LogicGuard output for report conclusions and cautious reuse claims.

## Timeline Contract

Required fields:

- `event_id`
- `event_type`
- `source_ref`
- `source_date`
- `coverage_period`
- `precedes`
- `supersedes`

Keep library accession time separate from source chronology.

## Freshness Contract

Required fields:

- `current_hashes`
- `validation_reports`
- `hash_bindings`
- `invalidated_by`
- `stale_evidence`

Validation is stale when a referenced file, model, contract, or report hash no
longer matches the current contract.

## Query Contract

Required fields:

- `query`
- `scope`
- `matches`
- `reason`

Empty results must include a reason and the inspected scope.

## Closure Contract

Required fields:

- `status`
- `evidence`
- `missing_inputs`
- `stale_evidence`
- `skipped_checks`
- `safe_claim`
- `unsafe_claim_boundary`
- `next_actions`

Allowed closure statuses:

- `pass`: current evidence supports the requested claim.
- `partial`: usable with stated boundaries.
- `blocked`: cannot support the requested claim.
- `downgraded`: a higher-level catalog/status claim exceeded current evidence.

A `pass` closure must include at least one evidence record and must not include
missing inputs, stale evidence, or skipped checks.

## Lifecycle States

Allowed lifecycle states:

- `candidate`
- `placeholder`
- `active_registered`
- `active_validated`
- `active_reusable`
- `blocked`
- `downgraded`
- `archived`
- `deprecated`
- `superseded`
- `rejected`

`active_validated` and `active_reusable` require a current passing closure
report. Terminal states must not be silently reopened.
