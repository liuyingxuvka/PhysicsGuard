"""Executable preflight for the PhysicsGuard purpose-template-pack change."""

from __future__ import annotations

from flowguard import (
    DuplicateBoundaryRisk,
    ExistingModelPreflight,
    ExistingOwnershipSnapshot,
    ModelContextHit,
    REUSE_DECISION_ADD_CHILD_MODEL,
    REUSE_DECISION_EXTEND_EXISTING,
    review_existing_model_preflight,
)


def current_asset_owner() -> ModelContextHit:
    return ModelContextHit(
        "physicsguard-expanded-starter-pack-owner",
        model_path="scripts/generate_expanded_starter_packs.py",
        evidence_id="source:expanded-starter-pack-generator@current-worktree",
        evidence_tier="source_current",
        responsibilities=(
            "declare reviewed PhysicsGuard domain pack content",
            "materialize hierarchical starter examples",
            "materialize generator-owned regression tests",
        ),
        function_blocks=("build_template", "write_yaml"),
        state_owned=("PACKS",),
        fields_owned=(
            "starter_pack.physical_content",
            "starter_pack.assumptions",
            "starter_pack.refinement_rules",
        ),
        side_effects_owned=(
            "write examples/hierarchical assets",
            "write generator-owned test modules",
        ),
        public_entrypoints=("scripts/generate_expanded_starter_packs.py",),
        validation_evidence=("tests/test_expanded_domain_starter_packs.py",),
    )


def correct_preflight() -> ExistingModelPreflight:
    return ExistingModelPreflight(
        "physicsguard-purpose-template-pack-preflight",
        "Add deterministic purpose-pack selection around existing PhysicsGuard assets",
        mode="full",
        model_search_performed=True,
        search_paths=(
            ".flowguard",
            "scripts/generate_expanded_starter_packs.py",
            "templates",
            "tests/test_expanded_domain_starter_packs.py",
            "openspec/changes/add-physicsguard-purpose-pack-builder",
        ),
        relevant_models=(current_asset_owner(),),
        ownership_snapshot=ExistingOwnershipSnapshot(
            function_block_owners=(
                ("build_template", "physicsguard-expanded-starter-pack-owner"),
                ("write_yaml", "physicsguard-expanded-starter-pack-owner"),
            ),
            state_owners=(("PACKS", "physicsguard-expanded-starter-pack-owner"),),
            field_owners=(
                ("starter_pack.physical_content", "physicsguard-expanded-starter-pack-owner"),
                ("starter_pack.assumptions", "physicsguard-expanded-starter-pack-owner"),
                ("starter_pack.refinement_rules", "physicsguard-expanded-starter-pack-owner"),
            ),
            side_effect_owners=(
                ("write examples/hierarchical assets", "physicsguard-expanded-starter-pack-owner"),
                ("write generator-owned test modules", "physicsguard-expanded-starter-pack-owner"),
            ),
            public_entrypoint_owners=(
                ("scripts/generate_expanded_starter_packs.py", "physicsguard-expanded-starter-pack-owner"),
            ),
        ),
        reuse_decision=REUSE_DECISION_EXTEND_EXISTING,
        downstream_routes=("model_first_function_flow", "development_process_flow"),
        rationale=(
            "Keep the existing generator as sole owner of physical starter-pack content and writes. "
            "Add a separate target-native selection/receipt adapter that references reviewed assets "
            "without cloning their equations, assumptions, or materialization path."
        ),
    )


def broken_parallel_generator_preflight() -> ExistingModelPreflight:
    return ExistingModelPreflight(
        "physicsguard-broken-parallel-template-generator",
        "Create another generator that rewrites existing starter assets",
        mode="full",
        model_search_performed=True,
        search_paths=("scripts/generate_expanded_starter_packs.py", "templates"),
        relevant_models=(current_asset_owner(),),
        ownership_snapshot=ExistingOwnershipSnapshot(
            state_owners=(("PACKS", "physicsguard-expanded-starter-pack-owner"),),
            side_effect_owners=(("write examples/hierarchical assets", "physicsguard-expanded-starter-pack-owner"),),
        ),
        reuse_decision=REUSE_DECISION_ADD_CHILD_MODEL,
        downstream_routes=("model_mesh_maintenance",),
        proposed_new_boundaries=("parallel-physicsguard-starter-pack-generator",),
        duplicate_risks=(
            DuplicateBoundaryRisk(
                "state",
                "PACKS",
                "physicsguard-expanded-starter-pack-owner",
                proposed_owner_id="parallel-physicsguard-starter-pack-generator",
            ),
            DuplicateBoundaryRisk(
                "side_effect",
                "write examples/hierarchical assets",
                "physicsguard-expanded-starter-pack-owner",
                proposed_owner_id="parallel-physicsguard-starter-pack-generator",
            ),
        ),
        rationale="The proposal duplicates existing content state and write ownership.",
    )


def run_checks():
    return (
        review_existing_model_preflight(correct_preflight()),
        review_existing_model_preflight(broken_parallel_generator_preflight()),
    )
