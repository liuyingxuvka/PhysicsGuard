## Why

PhysicsGuard has many reviewed starter assets, but an agent still has to choose and combine them ad hoc. A target-owned, validated purpose-template-pack builder will make reuse the default while failing closed when no safe match, composition, or native validation exists.

## What Changes

- Add a PhysicsGuard-owned template manifest that binds stable identities, applicability predicates, field ownership, composition rules, builders, validators, fixtures, and claim boundaries.
- Add deterministic zero/one/many candidate selection with an approved base/no-match path and explicit ambiguity/conflict terminals.
- Add canonical composition, one-owner-per-field enforcement, immutable selection and instance fingerprints, and unresolved-placeholder checks.
- Add PhysicsGuard-native manifest/selection/instance validation plus known-good and known-bad fixtures and focused tests.
- Add a target-owned, unsealed SkillGuard-neutral projection that is derived only after the current PhysicsGuard selector and preserves the complete native candidate inventory, content identities, and claim boundary.
- Preserve existing starter-pack generators and templates as domain assets; do not reinterpret template generation as physical-model validity or audit pass.

## Capabilities

### New Capabilities

- `physicsguard-purpose-template-packs`: PhysicsGuard-owned declaration, deterministic selection/composition, instantiation, fingerprinting, and native validation of reusable purpose template packs.

### Modified Capabilities

None.

## Impact

The change adds isolated Python modules, a target-owned manifest, a neutral projection adapter, new fixtures/tests, and FlowGuard evidence under this change. It does not modify OpenSpec, existing PhysicsGuard skill entrypoints, existing starter-pack templates, or the current expanded-starter-pack generator.
