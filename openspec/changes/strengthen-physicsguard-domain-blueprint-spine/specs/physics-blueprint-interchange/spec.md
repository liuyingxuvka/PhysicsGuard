## Purpose

Define the provider-neutral, content-addressed interchange boundary for PhysicsGuard blueprints and adapters while keeping PhysicsGuard's physical semantics separate from FlowGuard's generic blueprint, inventory, projection, and affected-reader ownership.

## ADDED Requirements

### Requirement: Canonical provider-neutral interchange
PhysicsGuard SHALL serialize one canonical physical-domain blueprint and review report to YAML and JSON without requiring a target programming language, vendor tool, or local source layout. Equivalent canonical YAML and JSON inputs SHALL produce the same logical identity, and target-specific details SHALL enter only through declared provider and artifact records.

The canonical local artifact root SHALL be the directory containing the blueprint and SHALL be declared as `artifact_root: blueprint_directory`. Every local `repo_path` MUST be a forward-relative path inside that directory. The loader MUST NOT infer a repository root, accept parent traversal, or retain an alternate legacy root convention.

#### Scenario: Vendor model uses an exchange package
- **WHEN** an adapter supplies a target revision, artifact inventory, physical elements, interfaces, and evidence from an official exchange package
- **THEN** PhysicsGuard can qualify the supplied physical semantics without requiring access to vendor source code

#### Scenario: Equivalent YAML and JSON are reviewed
- **WHEN** YAML and JSON documents contain the same canonical blueprint values
- **THEN** their review reports carry the same blueprint and logical-report fingerprints

#### Scenario: Example blueprint binds neighboring target artifacts
- **WHEN** the pump-loop blueprint is stored at `examples/testfile_contracts/pump_loop/pump_loop_physical_blueprint.yaml`
- **THEN** paths such as `model/pump_loop_hierarchy.yaml` and `contracts/clean_contract.yaml` resolve from that blueprint directory without `..` or a second root alias

### Requirement: Adapter results are capability-bound and content-addressed
Every observation or authority adapter result SHALL declare one provider id, provider kind, provider version, target-system id, subject revision, capability ids, exact input fingerprints, exact payload fingerprints, status, findings, and claim boundary. An adapter SHALL provide only its declared capabilities and MUST NOT self-license blueprint qualification.

#### Scenario: Adapter lacks a required capability
- **WHEN** the target blueprint requires interface topology but the selected provider declares only artifact inventory
- **THEN** interface topology remains a typed gap and no other provider or fallback is selected silently

#### Scenario: Adapter payload changes
- **WHEN** an adapter emits a new payload fingerprint for the same subject revision
- **THEN** every consuming blueprint result is stale until the changed payload is reviewed and rebound

#### Scenario: Provider claims its own result is complete
- **WHEN** a provider marks its payload complete but independent PhysicsGuard review finds missing semantics or bindings
- **THEN** the PhysicsGuard-derived status remains authoritative for the physical-domain claim

### Requirement: Portable physical-DNA export is deterministic and self-contained for declared queries
PhysicsGuard SHALL materialize one current `PhysicalBlueprintExportBundle` from an exact blueprint, frozen target-inventory authority, admitted canonical review, behavior-contract index, typed relation graph, and bounded evidence/resource manifest. The canonical bundle fingerprint SHALL exclude output path, archive metadata, wall-clock time, and formatting. Repeated export from identical logical inputs SHALL produce byte-identical canonical JSON and the same bundle fingerprint. The bundle SHALL preserve the frozen review status, deepest licensed layer, first gap, safe claim, identity-only bindings, stale/not-run states, and outside-scope members; it MUST NOT become a second reviewer, refresh evidence, or upgrade qualification.

The public bundle loader and query surface SHALL answer hierarchy, typed interface, state-transition, affected-impact, and reverse-trace questions using only bundle content. They SHALL NOT inspect the source repository, invoke a provider, run native validation, resolve an omitted artifact, or broaden an ambiguous query. A missing required object SHALL produce an exact portable-query gap rather than a guessed answer.

The default AI/CLI bundle projection SHALL be compact and SHALL expose only the bundle and frozen-source identities, review status, deepest licensed layer, structural-inventory counts, scenario-role coverage, domain-semantic coverage, independent-review coverage, claim-licensing coverage, first gap, safe claim, claim boundary, and measured canonical byte counts. The complete bundle SHALL remain on disk and MUST NOT be printed or injected into context by the default route. A deep query SHALL select exactly one current id in exactly one namespace: `module`, `element`, `case`, `impact`, or `reverse`. The result SHALL include only that bounded object or closure plus required ancestor/edge/gap context. Unknown, ambiguous, identity-only, unresolved, stale, and outside-scope terminals SHALL remain explicit. Every compact and deep projection SHALL report its own canonical serialized byte count and SHALL fail its projection budget rather than silently emit an unbounded payload.

#### Scenario: The same review is exported twice to different directories
- **WHEN** identical frozen blueprint inputs are exported to two different output paths
- **THEN** their canonical bytes and bundle fingerprints are identical and neither output path appears in logical identity

#### Scenario: Internal verifier consumes only the bundle
- **WHEN** a fresh verifier process receives the bundle in an isolated working directory with no PhysicsGuard repository or target files available
- **THEN** it checks the declared hierarchy, interface, pre-state/post-state, affected-impact, and reverse-trace fixtures exactly from the bundle and reports every unavailable fact as a bounded gap without asking an external agent

#### Scenario: A local binding is absent from the bundle
- **WHEN** a query requires source or evidence content that the bundle carries only as an identity reference
- **THEN** the consumer reports the exact identity-only boundary and does not follow a local path, scan a repository, or describe the referenced bytes as validated

#### Scenario: A blocked review is exported
- **WHEN** a caller deliberately exports a current non-pass review for handoff or diagnosis
- **THEN** the bundle preserves the non-pass status and first gap and cannot be used to claim static readiness

#### Scenario: An AI opens a bundle without a selector
- **WHEN** a consumer loads a valid bundle and supplies no deep selector
- **THEN** it receives only the compact frozen-status projection, including coverage denominators and the first gap, while the full bundle remains on disk

#### Scenario: An AI requests one exact deep object
- **WHEN** a consumer supplies exactly one current `module`, `element`, `case`, `impact`, or `reverse` id
- **THEN** it receives only that bounded detail or closure, the source bundle fingerprint, every relevant gap and claim boundary, and the measured canonical byte count

#### Scenario: A projection exceeds its token-oriented byte budget
- **WHEN** the canonical compact or deep projection is larger than its declared hard byte budget
- **THEN** the query fails with `portable_projection_budget_exceeded` and does not print the oversized projection or fall back to the full bundle

### Requirement: Native execution evidence is distinct from hash and schema integrity
A replayable native binding SHALL qualify an executable blueprint layer only when the declared PhysicsGuard owner executes the exact input and reproduces a terminal receipt bound to the native owner, operation, input fingerprint, target identity, subject revision, tool identity and version, terminal status, and terminal receipt fingerprint. Current bytes, successful native-schema parsing, or a provider envelope alone MUST NOT be reported as native execution.

#### Scenario: Typed artifact hash is current but no replay is bound
- **WHEN** a replayable test, validation, evidence, registry, library, or model-revision artifact has current bytes and subject identity but no exact native execution evidence
- **THEN** the binding is reported as unverified for executable qualification and contributes no native-owner replay coverage

#### Scenario: External provider observes exact bytes but owner cannot be replayed
- **WHEN** a current provider binds the exact external subject, revision, schema, obligations, and artifact fingerprint but the native owner is inaccessible
- **THEN** PhysicsGuard preserves a bounded external identity-only result and does not promote it to native execution

#### Scenario: Expected terminal receipt differs after replay
- **WHEN** the native owner executes but its actual terminal status or receipt fingerprint differs from the bound expectation
- **THEN** the binding is stale or blocked and the current executable claim fails

### Requirement: Direct native adapters preserve each authority's primary identity
Hierarchy, evidence registry, standalone project profile, test-file contracts and project index, signal mapping, logical dataset, model-dataset validation, model library, task-local model revision, and evidence-mesh adapters SHALL load their direct current schema and expose that schema's primary subject identity. The blueprint reviewer MUST NOT duplicate the native validator or use an enclosing registry, filename, alias, or summary count as a substitute identity.

#### Scenario: Standalone project profile is adapted
- **WHEN** a current project-profile authority is bound to a blueprint element
- **THEN** the adapter uses its profile id, target id, subject revision, and self-fingerprint without borrowing the project-evidence registry id

#### Scenario: Signal mapping is adapted
- **WHEN** a current signal-mapping ledger is bound to an interface path
- **THEN** the adapter uses the stable ledger id and native mapping review result rather than transient display rows

### Requirement: Module ledger reconciles the current registry denominator
The module/equation semantic-ledger checker SHALL derive its denominator directly from the current PhysicsGuard public module registry and require exactly one current independently reviewed semantic record and primary owner for every live registered type. Each physical module record SHALL state the module's `Input × State -> Set(Output × State)` contract; every actual declared input, configuration value, previous/current/next state, output residual and declared variable; complete equation and piecewise residual expressions with no undefined intermediate; normalization; explicit symbol-to-unit and reference conventions; exact constraints and valid/invalid regions; parameters; assumptions; invariants; effects; protected failures; diagnostics; exact implementation, concrete positive-test case, distinct counterexample case, instantiating example, typed resource, and source-independent oracle bindings; and stale conditions. A supporting framework record SHALL instead state its independently reviewable software/test behavior, allowed consumers, prohibited claims, exact implementation and tests, and stale conditions without inventing physical meaning. Stored counts and fingerprints SHALL be checked for freshness, and a caller-supplied subset, grouped family summary, class-name occurrence, source location, implementation-as-oracle assertion, or author-supplied reviewer label MUST NOT shrink the denominator or license semantic coverage.

The checker SHALL derive separate results for registry inventory, FunctionBlock completeness, equation dependencies and branches, units, constraints and regions, behavioral tests, counterexamples, independent oracles, and independent review. Physical semantic coverage SHALL be licensed only from the continuous conjunction of all required results for all physical members. Full and exact-module scopes SHALL preserve one checker/review identity; exact-module scope SHALL retain the global denominator but SHALL report global coverage as not evaluated and MUST NOT license it. Import, instantiation, test collection, structured-case execution, oracle execution, and independent-review replay SHALL be explicit isolated stages with `not_run`, failure, and terminal-success states kept distinct.

Behavioral and counterexample licensing SHALL come only from checker-owned execution of structured cases against the exact current registered module. The checker SHALL compare observed residual name, role, finite value, positive finite scale, diagnostic key, protected exception, or declared violation with the case contract. A real pytest that merely reaches residual behavior and performs `assert True`, or a caller-authored execution receipt, MUST NOT license behavior. Explicit pytest execution is separate evidence and the default review SHALL leave it `not_run`.

The implementation comparison SHALL use a source semantic IR that recursively resolves permitted pure helpers and local assignments and preserves reachable `if`, conditional-expression, value, scale, role, diagnostic, and return paths; unresolved/cyclic paths and operator, guard, or helper mutations SHALL block without variable-name fallback. A canonical runtime port contract SHALL independently carry input/output/previous/current/next-state direction, so coherent ledger-side role swaps fail. Constraint and region claims SHALL be executable closed predicates bound to implementation guards/failures and inside/boundary/outside cases. Unit claims SHALL use a canonical unit/meta-unit vocabulary, dimensional compatibility, and a registered independent project convention; coherent declaration-plus-ledger-authority fabrication SHALL fail.

Oracle licensing SHALL come only from checker-owned execution of every case through a restricted expression evaluator or one registered independent selector. Inputs, expected values, observed results, scales, and tolerances SHALL be finite, tolerances SHALL be nonnegative, and every observed result SHALL match within the declared tolerance. A module's own implementation or `residuals()` method MUST NOT be its sole resource or oracle, and a caller-embedded oracle result, self-hash, or receipt MUST NOT prove execution.

A record-content fingerprint proves only record currentness; it MUST NOT prove independent review. A semantic review SHALL consume a frozen request over the reviewed record and every implementation/test/example/resource/oracle input including the checker-owned oracle result, plus the fingerprint of the sole current closed reviewer-provider registry and its exact active-provider descriptor or explicit no-provider state. Only one registered independent reviewer producer MAY authorize the review by actually replaying that request, invoking the exact provider frozen by the registry, validating that provider's current tool and terminal result/receipt, and emitting its own terminal result and receipt bound to exact producer identity/version, request/input fingerprints, provider registry/tool/request/result/receipt fingerprints, command, exit status, concrete findings, disposition, and reviewer identity. Ledger-embedded labels, hashes, results, receipts, author-supplied reviewer identities, caller provider mappings, and caller-selected registries MUST NOT authorize pass; missing, `not_run`, failed, stale, self-authored, foreign, or mismatched producer/provider evidence remains blocked.

The sole current producer SHALL be `scripts/module_semantics_review_producer.py` with producer identity `physicsguard.module_semantics_review_producer.v1`. The checker MAY materialize the request only through explicit `--module MODULE --review-request-output REQUEST`. The producer SHALL consume only one frozen `physicsguard.module_semantics_review_request.v1` document through `python scripts/module_semantics_review_producer.py REQUEST --result RESULT --receipt RECEIPT` and SHALL emit at most one external `physicsguard.module_semantics_review_result.v1` document plus one external `physicsguard.module_semantics_review_receipt.v1` document. It SHALL replay every machine-decidable input fingerprint and all nine dimension results in the request, SHALL require all eight machine-decidable dimensions to pass before domain acceptance, and SHALL execute only the exact active provider frozen from the fixed `.physicsguard/module_semantics_reviewer_provider_registry.json`. The provider descriptor SHALL bind its id, owner, tool fingerprint, current signature algorithm, key id, and public verification key. The provider SHALL receive the exact frozen request plus the exact producer and provider commands and SHALL emit a full provider result and receipt body covered together with that complete execution request, exit, owner, disposition, and findings by one verifiable terminal signature. Public content fingerprints alone MUST NOT authorize execution. The producer SHALL verify the signature using only the frozen registry key, compare the signed exit with the exit it observed, and deterministically derive its outer result and receipt from that authenticated subject. It MUST NOT run implicitly from ordinary ledger review, write into the ledger, accept an alternate producer, accept a caller-supplied reviewer/provider mapping or registry path, accept an unsigned/self-hashed terminal, or mechanically approve domain truth. When the current production registry contains no real independently owned provider and public verification key, every real request SHALL remain terminal `blocked`. The checker SHALL default reviewer execution to `not_run` and SHALL only validate explicitly supplied `--review-result RESULT --review-receipt RECEIPT` external terminal artifacts against the exact current request. Before granting independent-review coverage for `accepted`, the checker SHALL independently require all eight machine dimensions to pass and independent review to remain `not_run`, verify the same signed terminal subject against the frozen registry key, reconstruct the provider verdict, reconstruct the sole deterministic producer result/receipt projection, and require the supplied outer pair to equal it exactly. It MUST reject a never-signed fingerprint with every public hash recomputed, a fully synthetic accepted pair, a copied signed result with altered command paths or receipt id, a fixture signature under any other registry public key, and an expected reviewer derived from the supplied result. It MUST NOT create, self-sign, repair, or substitute an accepted result or receipt.

For this patch upgrade, PhysicsGuard SHALL freeze and close all 152 members of the observed `default_module_registry()` baseline and SHALL keep the live public registry denominator at 152. The 39 members previously grouped as modeled SHALL be split and independently re-reviewed rather than grandfathered. The 37 mechanically draftable unresolved members MAY receive drafts derived from current code, tests, and examples, but each draft SHALL remain non-pass until a separate semantic review accepts or revises it. The 75 domain-judgment members SHALL be authored and reviewed explicitly. `DummyResidualModule` SHALL remain in the public default registry and public export as `supporting_framework_behavior`, SHALL carry `physical_claim_licensed=false`, and SHALL receive an independent software-behavior/test semantic record. It MUST NOT contribute to physical semantic coverage, physical blueprint readiness, validation depth, or a user-facing physical claim.

The current per-module schema and checker SHALL directly replace the old grouped `evidence_level: navigation` ledger. Runtime, documentation, tests, and project bindings SHALL accept only the current schema; PhysicsGuard SHALL NOT retain a legacy reader, converter command, dual emission, alias, compatibility registration, or second checker. The frozen and live public denominators SHALL both remain 152 for this patch unless a separately authorized breaking release changes the public contract. A future proposal to remove `DummyResidualModule` SHALL first inventory all callers, examples, tests, imports, and versioned contracts and obtain explicit breaking-change and version-strategy authority; direct removal SHALL NOT preserve an alias, fallback, or compatibility registry.

#### Scenario: One current registry member is omitted
- **WHEN** a ledger lists all previous members but omits one type returned by the current registry
- **THEN** reconciliation fails and identifies that exact unassigned member

#### Scenario: Every member is dispositioned but some remain unresolved
- **WHEN** the exact current denominator is reconciled but one or more members lack independent semantics, review, ownership, or exact bindings
- **THEN** reconciliation remains non-pass and broad modeled-coverage licensing is false

#### Scenario: A previous grouped member is grandfathered
- **WHEN** one of the 39 previously modeled types is covered only by a family-level navigation row or its historical status
- **THEN** current semantic-ledger review fails for that exact module and does not credit the family row

#### Scenario: A mechanical draft has no independent review
- **WHEN** one of the 37 mechanically draftable modules has a record copied or inferred from code, tests, and examples but no distinct current semantic-review result
- **THEN** the record remains a draft and contributes no independent-semantics coverage

#### Scenario: A structurally complete record has incomplete semantics
- **WHEN** a record has every required field but omits a declared variable, a residual output, an intermediate expression, a piecewise branch, an exact unit, a constraint boundary, or a distinct behavioral test/counterexample
- **THEN** structural inventory may pass but the exact semantic sub-result and physical semantic coverage fail for that module

#### Scenario: The implementation certifies itself
- **WHEN** the implementation source or `residuals()` method is the sole resource or oracle, the positive and counterexample bindings are the same semantic case, or the author/generator supplies only a reviewer label and content fingerprint
- **THEN** independent-oracle or independent-review closure fails and the record cannot license physical meaning

#### Scenario: A plausible caller-authored receipt is embedded
- **WHEN** a ledger author supplies terminal-looking behavioral, oracle, or review results, hashes, receipts, producer labels, and exit fields without the checker executing the registered owner
- **THEN** those payloads carry no licensing authority and the exact owning dimension remains `not_run` or blocked

#### Scenario: The current provider registry has no accepted provider
- **WHEN** the sole registered producer replays a request whose frozen current provider registry has no active independently owned provider
- **THEN** it emits a terminal blocked result and receipt, and an ordinary checker review reports independent review as not run or blocked rather than inventing a reviewer, accepting a caller mapping, or self-signing acceptance

#### Scenario: A registered provider executes successfully
- **WHEN** all eight machine-decidable dimensions pass and the sole producer executes the exact provider frozen from the current closed registry
- **THEN** accepted is possible only after the provider signs the complete execution/result/receipt terminal subject, the producer validates that signature and observed zero exit against the frozen public key, and the checker independently reconstructs the same verdict and exact outer artifacts from that authenticated subject

#### Scenario: Every public hash is recomputed without a provider signature
- **WHEN** a caller invents an unpublished execution fingerprint or synthesizes all provider and producer artifacts and recomputes every public content fingerprint
- **THEN** provider terminal verification fails because the frozen registry public key cannot verify the invented subject, and checker acceptance remains blocked

#### Scenario: A signed terminal is copied and its outer receipt is changed
- **WHEN** a caller copies an old valid signed terminal but changes the producer receipt id or producer/provider command paths and recomputes the unsigned outer hashes
- **THEN** checker reconstruction differs from the supplied pair or the signed subject no longer matches, so the external review fails

#### Scenario: Accepted artifacts retain a blocked machine dimension
- **WHEN** supplied producer-looking result and receipt claim accepted while the exact frozen request retains any blocked machine-decidable dimension
- **THEN** the checker fails the external evidence even if every caller-computable fingerprint is internally consistent

#### Scenario: An external terminal review is supplied
- **WHEN** the checker is explicitly given one result and one receipt from the sole producer
- **THEN** it verifies their schemas, producer identity, frozen request fingerprint, input and output fingerprints, all eight machine dimension states, empty producer findings for acceptance, frozen registry/provider authority, provider tool/request/result/receipt bindings, exit status, reviewer execution owner, domain findings, disposition, and terminal status before granting any independent-review coverage

#### Scenario: A no-op behavioral test is real and green
- **WHEN** an exact collectable pytest case selects a same-named fake module or calls residual behavior but its only assertion is unconditionally true
- **THEN** checker-owned structured-case execution fails to bind the current registered module and required observed fields, and neither pytest collection nor exit zero licenses behavior

#### Scenario: A coherent non-finite oracle is self-certified
- **WHEN** an oracle case, scale, tolerance, expected value, or result contains NaN or infinity, or its apparent success comes only from an embedded self-hash/receipt
- **THEN** oracle execution fails before semantic comparison and no independent-oracle coverage is granted

#### Scenario: Source syntax changes behind stable names
- **WHEN** a permitted helper, local assignment, `if`, conditional expression, local scale, or dynamic role keeps the same variable names while an operator, branch, returned diagnostic, or value changes
- **THEN** source semantic IR comparison fails the exact equation, FunctionBlock, or role owner; unresolved or cyclic expansion cannot fall back to names

#### Scenario: Ledger roles are swapped coherently
- **WHEN** input/output/state declarations, group lists, and ledger-local role authority are changed together but disagree with the canonical runtime port contract
- **THEN** FunctionBlock review fails the exact directions even though the ledger remains internally self-consistent

#### Scenario: Constraints or units are fabricated coherently
- **WHEN** arbitrary nonempty region prose or a copied unit is repeated in both the declaration and its ledger-local authority without an implementation guard/case or registered project convention
- **THEN** the constraint/region or unit result fails and physical semantic coverage remains blocked

#### Scenario: A binding only contains the class name
- **WHEN** a test or example binding merely contains the module class name but does not execute the exact behavior or instantiate the exact module successfully
- **THEN** that binding is rejected and the missing behavioral or example obligation remains visible

#### Scenario: A mutation corrupts physical meaning
- **WHEN** a known-bad fixture changes a unit, removes an equation definition or branch, drops a declared variable, marks a static module as a state transition, substitutes a registry-only test, or replaces an independent oracle/reviewer with the implementation author
- **THEN** the checker fails the exact semantic owner even when all paths and hashes are internally current

#### Scenario: Many modules are blocked at once
- **WHEN** a full-ledger check finds many record-level gaps
- **THEN** the default machine result remains token-bounded and reports the nine aggregate dimensions, counts, blocked module ids, per-record status/count, and first gap without embedding every detailed finding
- **AND** a caller MAY request the complete findings for one exact module from the same review identity, while an unknown module fails visibly and no second checker or alternate result authority is created

#### Scenario: A field has no behavior and another module owns the domain relation
- **WHEN** `RadiatorSimpleModule` previously read `fan_power_optional` and declared `fan_power_W` without using either in a locally owned residual while `RadiatorFanSimpleModule` owns the fan-power relation and the current caller inventory contains no dependent caller
- **THEN** the dead configuration and unbound variable are removed directly from `RadiatorSimpleModule`, supplying the retired flag fails visibly and points to `RadiatorFanSimpleModule`, and no alias, silent ignore, migration reader, fallback, or alternate fan-success path remains

#### Scenario: Dummy module is used as physical evidence
- **WHEN** a physical blueprint, module-coverage total, validation-depth result, or user-facing physical claim uses `DummyResidualModule` as physical evidence
- **THEN** the claim is rejected because its current disposition is `supporting_framework_behavior` and `physical_claim_licensed=false`

#### Scenario: Patch implementation removes the dummy public behavior
- **WHEN** this patch removes `DummyResidualModule` from the public export or `default_module_registry()` or reduces the live public denominator below 152 for that reason
- **THEN** compatibility and release closure block because no breaking-change or version-strategy authority exists

#### Scenario: A new domain example uses the dummy as a physical model
- **WHEN** a new or materially revised user-facing domain example introduces `DummyResidualModule` as though it represented physical behavior
- **THEN** example review blocks and requires a genuine low-fidelity physical module while preserving existing patch-compatible callers

#### Scenario: Future retirement is proposed
- **WHEN** a later change proposes to remove the dummy public behavior
- **THEN** it is treated as an explicit breaking-change candidate with caller inventory, example/test migration, and version-strategy approval, and no alias, fallback, or compatibility registry may substitute for direct removal

#### Scenario: Navigation schema is supplied
- **WHEN** the old grouped ledger or `evidence_level: navigation` shape is supplied to the current checker
- **THEN** it fails visibly as a retired schema and is not converted or read through another path

### Requirement: Target-specific adapters converge on one review path
Native, YAML, JSON, user-owned template, and official target-tool adapters SHALL produce the current canonical blueprint input or capability-bound provider results. All accepted inputs SHALL converge on the single `blueprint review` command and one native reviewer; adapters MUST NOT expose an alternate success path, compatibility reader, or target-specific qualification owner.

#### Scenario: Native adapter emits canonical input
- **WHEN** a target-native adapter successfully observes its declared capabilities
- **THEN** its output is reviewed by the same canonical command and native predicates as a manually supplied canonical blueprint

#### Scenario: Adapter cannot observe a required member
- **WHEN** the provider cannot access an in-boundary module, equation, signal, file, or test
- **THEN** it emits an unsupported or unresolved disposition with reason and the canonical reviewer preserves the gap

### Requirement: PhysicsGuard runtime remains independent of FlowGuard
The installable PhysicsGuard product SHALL own physical-domain schema, semantics, review, qualification, and interchange without importing or requiring the FlowGuard package at runtime. FlowGuard SHALL remain the owner of generic implementation inventory, software-blueprint structure, generic target-system composition, generic affected projection, and generic understanding summaries.

#### Scenario: PhysicsGuard is installed without FlowGuard
- **WHEN** a user installs and runs the supported PhysicsGuard blueprint review runtime without FlowGuard
- **THEN** native physical blueprint review works and reports only PhysicsGuard-owned domain claims

#### Scenario: Generic blueprint behavior would be duplicated
- **WHEN** an implementation proposal adds a second generic inventory, generic software owner graph, generic affected reader, or generic readiness engine inside PhysicsGuard
- **THEN** the change is rejected in favor of the FlowGuard-owned boundary or a PhysicsGuard-only semantic extension

### Requirement: FlowGuard projection is later-bound and authority-preserving
A FlowGuard projection MAY consume a qualified PhysicsGuard blueprint only after the selected FlowGuard source, installed runtime, schema, and public blueprint interfaces are frozen and verified. The projection SHALL be implemented at the project or integration boundary, SHALL NOT add a PhysicsGuard product runtime dependency, SHALL preserve the PhysicsGuard blueprint and receipt fingerprints, and SHALL NOT recompute or override physical semantics.

#### Scenario: FlowGuard toolchain is dirty or drifting
- **WHEN** the installed FlowGuard import resolves to an unfrozen or concurrently modified checkout
- **THEN** FlowGuard projection work remains blocked while native PhysicsGuard blueprint implementation and validation MAY continue independently

#### Scenario: Stable FlowGuard consumes a qualified blueprint
- **WHEN** the FlowGuard source and install identity are frozen and the PhysicsGuard blueprint is current
- **THEN** the integration projects PhysicsGuard physical semantics into FlowGuard's generic layers without copying FlowGuard's engine into PhysicsGuard

#### Scenario: Projection attempts to upgrade physical status
- **WHEN** the PhysicsGuard report is incomplete, stale, or blocked
- **THEN** the FlowGuard projection preserves that status and cannot promote the physical-domain claim

### Requirement: Interchange excludes secrets and unbounded production content
Canonical interchange SHALL carry bounded identities, independent semantics, fingerprints, and authorized resource references. It MUST NOT require embedded production source, secrets, credentials, proprietary binary content, or unrestricted external paths to establish blueprint identity.

#### Scenario: Provider returns a secret-bearing payload
- **WHEN** an adapter payload contains credentials or other forbidden secret fields
- **THEN** interchange review blocks the payload before it can enter the blueprint

#### Scenario: External artifact cannot be copied
- **WHEN** an authoritative target artifact must remain in its owner-controlled location
- **THEN** the blueprint records an authorized external reference, provider identity, fingerprint, and access gap without copying the artifact

### Requirement: Native adapters emit one provider-neutral source census
Every object-DNA-capable native adapter SHALL emit the complete source census it can directly observe from the governed object, independently of caller-selected expected members, model elements, mappings, or affected scope. Each census member SHALL carry a stable source id, kind, locator, role, content or contract fingerprint, and any bounded semantic fact owned by that adapter. The canonical reviewer SHALL consume this contract without depending on FMI, Python, Modelica, or any vendor-specific schema.

#### Scenario: FMI expected subsets are synchronously reduced
- **WHEN** an FMI request reduces expected members or variables while the actual FMU bytes remain unchanged
- **THEN** the native result still exposes every discovered archive member and XML variable and object-DNA mapping coverage cannot shrink with the request

#### Scenario: Another tool provides a source census
- **WHEN** a non-FMI adapter for another language, experiment, testbench, document-backed model, or workflow emits the current source-census contract
- **THEN** the same canonical object-DNA reviewer accepts it without an FMI or Python special case

### Requirement: Portable object-DNA bundles preserve compact closure evidence
An object-DNA bundle SHALL include a compact projection of source-census identities and fingerprints, source-to-model mappings and terminal dispositions, native behavior-result links, requested understanding target, declared-consistency status, object-DNA readiness, and first gap. It SHALL NOT embed governed binaries or unbounded source bytes merely to make the bundle self-contained.

#### Scenario: Internal verifier reads an object-DNA bundle
- **WHEN** a fresh verifier process receives only a portable bundle
- **THEN** it distinguishes declared model structure from observed source coverage, follows source-to-model and model-to-source links, inspects native result bindings, and states the exact readiness boundary without repository access or external-agent input
