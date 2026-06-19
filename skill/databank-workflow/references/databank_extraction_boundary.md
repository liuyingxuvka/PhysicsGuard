# DataBank Extraction Boundary

Use this file when deciding whether work belongs in DataBank or a Guard-specific
skill. The guiding rule is simple: PhysicsGuard owns physical evidence;
DataBank owns the total database ledger above evidence providers.

## Stays In PhysicsGuard

| Responsibility | Reason |
| --- | --- |
| Test-file manifests, field counts, row counts, and file hashes | These are physical/test-data facts. |
| Test-file contracts, units, parameter roles, and field-to-model binding | These prove whether a measured signal is understood correctly. |
| Physical model hierarchy, parent/child models, residual validation, and model-library evidence | These are physical model and validation concerns. |
| Project evidence registry details for tests, signals, and model targets | These feed DataBank but remain PhysicsGuard-owned evidence. |

## Moves To DataBank

| Responsibility | Reason |
| --- | --- |
| Database root policy, catalog, status, history, and handoff | These are total-ledger records, not physical validation proof. |
| Project intake/admission lifecycle state | This decides how a project appears in the database ledger. |
| Query gate and AI navigation index | These help agents find evidence across providers. |
| Freshness, closure, downgrade, and stale-proof propagation | These decide whether higher-level claims can still be trusted. |
| Cross-Guard source/data/model/binding/logic/timeline contract table | These normalize evidence from multiple Guard workflows. |

## Changes In Existing PhysicsGuard Database Skills

- Keep them as compatibility and provider-evidence routes.
- Change their trigger language so broad database work routes to
  `databank-workflow`.
- Preserve existing PhysicsGuard CLI command examples as bridge commands only.
- State that PhysicsGuard database success is not sufficient for cross-Guard
  freshness, closure, or reusable database proof.

## Explicitly Prohibited

- Do not copy raw large source, test, or simulation data into the database by
  default.
- Do not use AI-only summaries in place of generated manifests, contracts, or
  check reports.
- Do not allow a catalog or status file to claim `validated`, `reusable`, or
  `pass` when lower-level closure is blocked, stale, missing, skipped, or
  outside the requested claim boundary.
- Do not hardcode a domain taxonomy in the skill. Store generic tags and
  project-specific policy metadata instead.

## Initial Migration Order

1. Freeze this boundary.
2. Create DataBank skill skeleton and scripts.
3. Route total-ledger database entrypoints to DataBank.
4. Add freshness and closure checks.
5. Add AI navigation.
6. Connect LogicGuard, TraceGuard, SourceGuard, FlowGuard, and PhysicsGuard
   evidence through the common closure envelope.

## Current Implementation Boundary

The DataBank skill now includes deterministic root-layout, contract,
provider-adapter, freshness, closure, lifecycle, navigation, query, and
one-command audit scripts. It still does not perform Guard-specific proof
itself. PhysicsGuard, LogicGuard, TraceGuard, SourceGuard, and FlowGuard remain
the owners of their provider evidence; DataBank records and gates their current
closure status.
