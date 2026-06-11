## Context

The current hierarchy is:

- Test-file contracts own one physical file's fields, units, roles, and model
  mappings.
- Project evidence registries own one project's files, facts, contexts,
  bindings, bundles, and gaps.
- Model libraries own reusable model assets and validation evidence.

The missing layer is a database-level catalog that indexes many project
registries and model libraries so AI agents can search, compare, and maintain
the collection without rereading every project from scratch.

## Design Decisions

### Decision: Catalog is a map, not a data warehouse

The first version is a YAML/JSON catalog. It stores project references, tags,
lightweight summaries, confidence states, and gap state. It must not embed raw
test-data rows or copy large datasets.

### Decision: Project registry remains authoritative

Project-level details remain in `ProjectEvidenceRegistry`. The database catalog
may cache summaries and indexes, but it must cite the project registry path and
surface stale or missing registry state.

### Decision: Tags are generic and user/AI supplied

The catalog uses generic fields such as `domain_tags`, `system_tags`,
`subsystem_tags`, `component_tags`, `test_object_tags`, `testbench_tags`, and
`measurement_tags`. It does not hardcode any domain-specific taxonomy.

### Decision: Confidence is split by concern

The catalog records separate confidence/freshness signals for source evidence,
mapping evidence, data quality, validation, reuse, and catalog freshness. It
does not collapse them into one misleading score.

### Decision: Query output keeps gaps visible

Database queries return matching projects and the relevant gap summary. Query
results are navigation aids and do not prove that two projects are directly
comparable.

### Decision: Catalog refresh is read-only in v1

Refresh derives summaries from project registries and model libraries, then
reports what would be current. It does not mutate the catalog automatically.

## FlowGuard Plan

Add a database catalog model that covers:

- locating the catalog;
- registering project references;
- loading project evidence registries;
- deriving cross-project indexes;
- running catalog gap checks;
- building the database map;
- gating query and cross-project comparison claims.

Key invariants:

- no cross-project query/comparison claim without catalog gap check;
- no claim that a project is complete without a project registry or explicit
  missing-registry reason;
- no raw data payload embedded in catalog metadata;
- no validated/reusable claim when a referenced project has blocking gaps;
- no direct comparability claim when comparison scope is unknown;
- database map remains navigation and not validation proof.

## Risks

- Catalog summaries can become stale. Mitigation: include `last_scanned_at`,
  `stale_reason`, registry digest, and gap checks.
- Tags can drift across projects. Mitigation: keep a tag dictionary/alias area
  and treat unknown tags as reviewable metadata rather than hard failures.
- AI may overclaim cross-project comparability. Mitigation: query and map
  outputs include claim-boundary text and gap counts.
