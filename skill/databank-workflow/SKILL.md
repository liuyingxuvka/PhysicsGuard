---
name: databank-workflow
description: Guard-neutral database workflow for building, auditing, querying, navigating, and handing off project evidence databases across PhysicsGuard, LogicGuard, TraceGuard, SourceGuard, and FlowGuard. Use when Codex needs database roots, catalogs, project intake, lifecycle status, freshness, closure, AI navigation, query gates, or cross-Guard evidence ledgers; do not use for raw physical validation itself.
---

# DataBank Workflow

DataBank is the total ledger above Guard-specific proof. It records where
evidence lives, which contracts exist, which proof is fresh, what can be
claimed, and what future AI agents should read first.

## Route Boundary

- Use DataBank for database root, catalog, status, history, handoff, project
  intake, lifecycle state, query gates, AI navigation, freshness, and closure.
- Use PhysicsGuard for test-file manifests, fields, units, parameter roles,
  field-to-model bindings, physical models, residual validation, and model
  library evidence.
- Use LogicGuard for report-claim support, assumptions, limits, rebuttals, and
  unsafe conclusion boundaries.
- Use TraceGuard for chronology, version replacement, supersession, and
  timeline conflict evidence.
- Use SourceGuard for source discovery, provenance, source gaps, and source
  coverage.
- Use FlowGuard for process, route, model, validation freshness, and final
  claim gating when workflow state or evidence validity changes.

Read `references/databank_extraction_boundary.md` when changing or disputing
the PhysicsGuard/DataBank boundary. Read `references/contracts.md` before
creating or validating a database record.

## Required Output Shape

Every downstream Guard result DataBank ingests must use this envelope:

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

Do not claim a project is validated, reusable, or pass if any required provider
result is blocked, stale, missing, skipped, or outside the requested claim
boundary.

## Workflow

1. Confirm the user intends an explicit database root or project evidence
   ledger. Do not treat the whole computer or prior chats as an implicit hidden
   database.
2. Build or refresh metadata-only registries. Keep raw source and test data in
   their original locations; store paths, hashes, summaries, and evidence refs.
3. Collect contracts for source, data, model, binding, logic, timeline,
   freshness, query, and closure.
4. Run deterministic checks from `scripts/` before making broad claims:
   - `databank_root_check.py` for explicit root initialization/layout checks.
   - `databank_intake.py` for metadata-only project intake scaffolding.
   - `databank_contract_check.py` for required-field checks on source, data,
     model, binding, logic, timeline, freshness, query, and closure contracts;
     use `--check-paths` when local path validity is part of the claim.
   - `databank_provider_adapter.py` for converting Guard provider reports into
     the shared DataBank closure envelope without hiding provider gaps.
   - `databank_freshness_check.py` for file/model/contract/report hash
     freshness.
   - `databank_closure_check.py` for provider envelope and catalog downgrade
     checks.
   - `databank_lifecycle.py` for dry-run or applied lifecycle transitions with
     append-only history events.
   - `databank_nav_render.py` for `PROJECT_NAV_INDEX.md` generation and link
     validation.
   - `databank_query.py` for query results with explicit empty-result reasons.
   - `databank_audit.py` for a one-command root, contract, provider, closure,
     freshness, navigation, and query audit.
5. Render or update the AI navigation index so a future agent can find sources,
   test data, models, validation, report claims, timelines, and query surfaces
   without guessing paths.
6. End with a closure status: `pass`, `partial`, `blocked`, or `downgraded`.
   Report skipped checks and unsafe claim boundaries explicitly.

## Command Quick Start

Run scripts by absolute path or from the skill directory. Prefer JSON for
machine-stable inputs and outputs.

```powershell
python scripts/databank_root_check.py DATABASE_ROOT --init --database-id DATABASE_ID --pretty
python scripts/databank_contract_check.py CONTRACTS.json --check-paths --base DATABASE_ROOT --pretty
python scripts/databank_provider_adapter.py PROVIDER_REPORT.json --provider physicsguard --output PROVIDER_CLOSURE.json --pretty
python scripts/databank_intake.py PROJECT_ROOT --database DATABASE_ROOT --output REGISTRY.json --pretty
python scripts/databank_freshness_check.py FRESHNESS.json --pretty
python scripts/databank_closure_check.py --provider PROVIDER.json --catalog CATALOG.json --pretty
python scripts/databank_lifecycle.py DATABASE_ROOT PROJECT_ID --state active_registered --reason "registered evidence" --apply --pretty
python scripts/databank_nav_render.py NAV.json --output PROJECT_NAV_INDEX.md --pretty
python scripts/databank_query.py CATALOG.json --field id --value PROJECT_ID --pretty
python scripts/databank_audit.py DATABASE_ROOT --query id=PROJECT_ID --pretty
```

## Root Layout

A complete DataBank root contains:

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

Use `databank_root_check.py --init` to create the layout. Do not treat a
folder without this explicit structure as an implicit database.

## Compatibility With PhysicsGuard Database Commands

Existing `physicsguard.cli database` commands may still be useful bridge
commands for old PhysicsGuard databases. Treat their output as provider or
compatibility evidence, not as DataBank closure. Run DataBank freshness and
closure checks before making cross-Guard or reusable database claims.

## Prohibited Shortcuts

- Do not copy raw large datasets into the database by default.
- Do not replace scripted manifests, contracts, or checks with AI-only oral
  summaries.
- Do not let a high-level catalog hide project-level blocked, stale, missing,
  or skipped proof.
- Do not hardcode an industry taxonomy into the skill; use project metadata and
  generic tags unless a project-level policy says otherwise.
- Do not claim a real project database has been migrated until the explicit
  root audit, provider adapter output, closure report, lifecycle history, and
  navigation validation have passed on that real database root.
