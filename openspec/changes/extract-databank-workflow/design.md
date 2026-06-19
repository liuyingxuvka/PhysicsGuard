## Context

The existing PhysicsGuard database implementation is useful as a legacy
provider for physical/test/model evidence, but the user wants a fuller database
workflow that future AI agents can operate before the real database path is
available. The implementation must improve what can be improved now, while
leaving real project migration to a later AI once the actual database root is
found.

## Design Decisions

### Decision: DataBank is a skill-level workflow with deterministic scripts

DataBank is delivered as a Codex skill with scripts, references, examples, and
tests. This keeps the workflow immediately usable by future agents without
requiring a new package namespace before real database migration work begins.

### Decision: The root layout is explicit and file-backed

A DataBank database root contains:

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

No folder is a DataBank database merely because it exists on disk or appeared
in an earlier chat.

### Decision: Provider outputs enter through a shared closure envelope

Every Guard provider must be converted to:

- `status`
- `evidence`
- `missing_inputs`
- `stale_evidence`
- `skipped_checks`
- `safe_claim`
- `unsafe_claim_boundary`
- `next_actions`

DataBank may adapt provider reports into this envelope, but it must not hide
missing, stale, skipped, partial, or blocked provider evidence.

### Decision: Lifecycle changes are history-backed

Lifecycle transitions are dry-run by default and write only with explicit apply.
`active_validated` and `active_reusable` require passing closure evidence.
Terminal states cannot be silently reopened.

### Decision: Broad claims are gated by current evidence

The one-command audit aggregates root, contracts, provider closure, freshness,
navigation, and query checks. Any blocked/stale/skipped/missing lower-level
evidence prevents broad validated/reusable/pass claims.

## Deferred Work

- Real database migration and real project audit require the actual database
  root path.
- Deep provider-specific semantic extraction remains owned by PhysicsGuard,
  LogicGuard, TraceGuard, SourceGuard, and FlowGuard.
- A standalone Python package namespace can be considered later if DataBank
  grows beyond a skill workflow.

## FlowGuard Plan

Use FlowGuard to model the critical claim boundary:

- provider result input changes closure state;
- broad catalog/lifecycle claims require current passing closure;
- blocked provider evidence downgrades or blocks broad claims;
- root/layout checks must happen before audit pass;
- lifecycle promotion to validated/reusable requires passing closure;
- background or skipped evidence does not count as completion.

Model-test alignment compares these model obligations with the DataBank script
tests and fixture audit.
