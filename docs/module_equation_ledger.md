# Per-Module Semantic Ledger

PhysicsGuard keeps its sole current public-module semantic authority at
`.physicsguard/module_equation_ledger.yaml`. The name is retained as the stable
project path, but the old grouped `evidence_level: navigation` content is
retired. The current schema is
`physicsguard.module_semantics_ledger.v2` and has exactly one independently
reviewed record for every type returned by
`physicsguard.modules.registry.default_module_registry()`.

## What The Ledger Answers

For one exact module type, the record answers:

- what input and state it consumes, what output or next state it can produce,
  what effects it has, and what it rejects;
- which equation or residual it checks and how that residual is normalized;
- which symbols, SI units, reference or sign convention, parameters, and
  constraints apply;
- which assumptions, invariants, valid regions, invalid regions, protected
  failures, and diagnostic keys bound the claim;
- which implementation class, tests, counterexamples, examples, resources,
  and executable oracle own the current behavior;
- who owns the module semantics, how the record was authored and independently
  reviewed, and what changes make the review stale.

This lets an AI read one affected module record instead of loading every module
or trusting a family-level summary. A family summary may still be derived for
navigation, but it owns no semantics and licenses no coverage.

## Frozen Patch Baseline

The current patch freezes the live public registry at 152 members:

| Partition | Count | Current requirement |
| --- | ---: | --- |
| previously grouped | 39 | split into 39 records and independently re-reviewed; no grandfathered family pass |
| mechanically draftable | 37 | source/test/example draft stays non-authoritative until a distinct semantic reviewer accepts it |
| domain judgment | 75 | equation, units, assumptions, limits, failures, diagnostics, and evidence applicability are reviewed explicitly |
| supporting framework behavior | 1 | `DummyResidualModule` retains only its software/test behavior |

The checker derives the live denominator from the registry, compares it with
the frozen count and membership fingerprint, checks the four exact partitions,
and then requires 152 unique records and 152 unique primary owners. A caller
cannot pass a smaller list, a family row, or a stored count to shrink that
denominator.

## DummyResidualModule Boundary

`DummyResidualModule` remains a public export and remains in the default
registry for this patch because existing framework tests and fixtures consume
that behavior. Its one record is classified exactly as
`supporting_framework_behavior` and sets
`physical_claim_licensed: false`.

It may support framework, registry, solver, residual, and diagnostic plumbing
tests. It may not support a physical blueprint, physical validation depth,
physical semantic coverage, or a user-facing physical conclusion. The current
software/registry denominator is therefore 152, while the physical semantic
denominator is 151. Removing the dummy is a future breaking-change decision,
not an alias, fallback, or silent registry change in this patch.

The ledger also freezes the paths and fingerprints of the 19 existing examples
that still mention the dummy. A new dummy-backed example or a changed existing
one fails until an independent review either confirms framework-only use or
replaces it with a genuine low-fidelity physical module.

## Independent Review And Freshness

The 37 mechanically derived records identify their draft author and state that
the draft itself is non-authoritative. Their semantic reviewer must be a
different owner. The old 39 records require `independent_re_review`; the 75
domain records require `independent_domain_review`; the dummy requires an
independent software-behavior review. A historical family label cannot satisfy
any of these checks.

Implementation, test, counterexample, example, and resource bindings include a
repository-relative path, an exact selector, and the current file fingerprint.
The semantic review also fingerprints the record it accepted. A changed class,
test, example, registry fingerprint, equation, unit, validity boundary,
diagnostic, owner, or claim license therefore makes the record fail visibly
until it is reviewed again.

## Check The Current Authority

Run:

```powershell
python scripts/check_module_equation_ledger.py --json
```

A pass reports:

- 152 live registry members and 152 semantic records;
- partition counts `39 / 37 / 75 / 1`;
- a 151-member physical semantic denominator;
- `dummy_physical_claim_licensed: false`;
- separately licensed software/registry and physical semantic coverage.

The checker accepts no legacy reader, converter, grouped unresolved bucket,
alias, dual emission, or alternate checker. The tests include known-bad cases
for missing and duplicate records, grouped rows, the retired navigation schema,
self-approved mechanical drafts, incomplete domain records, dummy-backed
physical claims, and stale implementation or review fingerprints.

## Claim Boundary

A passing ledger proves current per-module semantic and binding closure for the
152-member public registry. It does not by itself prove high-fidelity physical
correctness, reproduce a commercial solver, execute every bound test, verify an
installed package, or establish Git, tag, GitHub, or release state. Those are
separate evidence and lifecycle gates.
