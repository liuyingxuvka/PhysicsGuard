"""Generate the current receipt-only SkillGuard contract for the PhysicsGuard parent."""

from __future__ import annotations

import json
from pathlib import Path

from verify_physicsguard_suite_parent import EXPECTED_SKILLS


ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = ROOT / ".flowguard" / "skillguard-parent"
CONTROL_ROOT = PARENT_ROOT / ".skillguard"
MODEL_PATH = ".flowguard/skillguard-parent/.skillguard/contract_model.py"
ROUTE_ID = "route:physicsguard-skill-suite-parent:receipt-only"
FUNCTION_ID = "function:physicsguard-skill-suite-parent:receipt-only"
OWNER_ID = "physicsguard.skill-suite-parent"
PARENT_SKILL_ID = "physicsguard-skill-suite-parent"
PARENT_UNIT_ID = "unit:physicsguard-skill-suite-parent"
CLAIM_BOUNDARY = (
    "This parent consumes current child closure and installation receipts for all ten "
    "maintained PhysicsGuard skills and the existing suite ModelMesh. It launches no "
    "child model proof and does not interpret PhysicsGuard semantics."
)


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _child_ids(skill_id: str) -> tuple[str, str, str, str]:
    suffix = skill_id.removeprefix("physicsguard-")
    return (
        f"step:physicsguard-skill-suite-parent:consume:{suffix}",
        f"check:physicsguard-skill-suite-parent:consume:{suffix}",
        f"semantic:physicsguard-skill-suite-parent:consume:{suffix}",
        f"obligation:physicsguard-skill-suite-parent:consume:{suffix}",
    )


def _model() -> dict[str, object]:
    child_rows = [_child_ids(skill_id) for skill_id in EXPECTED_SKILLS]
    mesh_step = "step:physicsguard-skill-suite-parent:reattach-model-mesh"
    mesh_obligation = "obligation:physicsguard-skill-suite-parent:reattach-model-mesh"
    steps = [
        {
            "step_id": step_id,
            "route_id": ROUTE_ID,
            "owner_id": OWNER_ID,
            "action_kind": "receipt_replay",
            "terminal_kind": "",
            "prerequisite_step_ids": [],
        }
        for step_id, _check_id, _semantic_id, _obligation_id in child_rows
    ]
    steps.extend(
        [
            {
                "step_id": mesh_step,
                "route_id": ROUTE_ID,
                "owner_id": OWNER_ID,
                "action_kind": "mesh_reattachment",
                "terminal_kind": "",
                "prerequisite_step_ids": [row[0] for row in child_rows],
            },
            {
                "step_id": "terminal:physicsguard-skill-suite-parent:current",
                "route_id": ROUTE_ID,
                "owner_id": OWNER_ID,
                "action_kind": "terminal",
                "terminal_kind": "success",
                "prerequisite_step_ids": [mesh_step],
            },
            {
                "step_id": "terminal:physicsguard-skill-suite-parent:blocked",
                "route_id": ROUTE_ID,
                "owner_id": OWNER_ID,
                "action_kind": "terminal",
                "terminal_kind": "blocked",
                "prerequisite_step_ids": [],
            },
        ]
    )
    obligations = [
        {
            "obligation_id": obligation_id,
            "invariant_id": obligation_id.replace("obligation:", "invariant:", 1),
            "owner_step_ids": [step_id],
            "required": True,
        }
        for step_id, _check_id, _semantic_id, obligation_id in child_rows
    ]
    obligations.append(
        {
            "obligation_id": mesh_obligation,
            "invariant_id": mesh_obligation.replace("obligation:", "invariant:", 1),
            "owner_step_ids": [mesh_step],
            "required": True,
        }
    )
    return {
        "schema_version": "skillguard.flowguard_model_export.v2",
        "flowguard_schema_version": "1.0",
        "model_id": "physicsguard-skill-suite-parent.receipt-only.current",
        "parent_model_id": "physicsguard.guard-family.family-baseline-regression.current",
        "functions": [
            {
                "function_id": FUNCTION_ID,
                "business_intent": (
                    "Consume ten current family-baseline terminal-success child closures and "
                    "prove their receipt-only reattachment to the PhysicsGuard suite mesh; "
                    "this parent cannot close a concrete current model."
                ),
                "owner_id": OWNER_ID,
                "route_ids": [ROUTE_ID],
            }
        ],
        "routes": [
            {
                "route_id": ROUTE_ID,
                "function_id": FUNCTION_ID,
                "owner_id": OWNER_ID,
                "step_ids": [row[0] for row in child_rows]
                + [
                    mesh_step,
                    "terminal:physicsguard-skill-suite-parent:current",
                    "terminal:physicsguard-skill-suite-parent:blocked",
                ],
                "success_terminal_step_id": "terminal:physicsguard-skill-suite-parent:current",
                "blocked_terminal_step_id": "terminal:physicsguard-skill-suite-parent:blocked",
                "handoffs": [],
            }
        ],
        "steps": steps,
        "obligations": obligations,
        "invariant_ids": [row["invariant_id"] for row in obligations],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _selectors(skill_id: str) -> list[dict[str, str]]:
    base = f"skill/{skill_id}"
    paths = [
        "scripts/verify_physicsguard_suite_parent.py",
        "scripts/verify_guard_simulation_readiness.py",
        ".flowguard/physicsguard_v1_retirement_inventory.json",
        ".flowguard/physicsguard_suite_parent_inventory.json",
        f"{base}/SKILL.md",
        f"{base}/.skillguard/contract-source.json",
        f"{base}/.skillguard/compiled-contract.json",
        f"{base}/.skillguard/check-manifest.json",
        f".flowguard/retirement-receipts/{skill_id}.json",
        f"{base}/guard-model/contract.json",
        f"{base}/guard-model/candidate.json",
        f"{base}/guard-model/oracles.json",
        f"{base}/guard-model/known-good.json",
        f"{base}/guard-model/known-bad.json",
        f"{base}/guard-model/verify.py",
    ]
    return [{"kind": "path", "path": path} for path in paths]


def _source(model: dict[str, object]) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    bindings: list[dict[str, object]] = []
    obligations: list[str] = []
    child_check_ids: list[str] = []
    for skill_id in EXPECTED_SKILLS:
        step_id, check_id, semantic_id, obligation_id = _child_ids(skill_id)
        obligations.append(obligation_id)
        child_check_ids.append(check_id)
        checks.append(
            {
                "check_id": check_id,
                "semantic_check_id": semantic_id,
                "kind": "command",
                "command": "python",
                "args": [
                    "scripts/verify_physicsguard_suite_parent.py",
                    "verify-child",
                    "--repository-root",
                    "{{repository_root}}",
                    "--skill-id",
                    skill_id,
                ],
                "cwd_token": "repository_root",
                "expected": {"exit_code": 0},
                "timeout_seconds": 120,
                "evidence_class": "hard",
                "evidence_domain_id": "physicsguard-skill-suite-parent:receipt-replay",
                "execution_owner_id": f"owner:physicsguard-skill-suite-parent:consume:{skill_id}",
                "covers_obligation_ids": [obligation_id],
                "depends_on_check_ids": [],
                "input_selectors": _selectors(skill_id),
                "maintenance_unit_id": PARENT_UNIT_ID,
                "member_skill_id": PARENT_SKILL_ID,
                "evidence_subject_id": (
                    f"subject:physicsguard-skill-suite-parent:consume:{skill_id}"
                ),
            }
        )
        bindings.append(
            {
                "step_id": step_id,
                "check_ids": [check_id],
                "output_artifact_ids": [],
                "action": {
                    "kind": "receipt_replay",
                    "summary": f"Read-only replay of {skill_id} closure and installation currentness.",
                },
            }
        )
    mesh_obligation = "obligation:physicsguard-skill-suite-parent:reattach-model-mesh"
    obligations.append(mesh_obligation)
    mesh_check = "check:physicsguard-skill-suite-parent:reattach-model-mesh"
    checks.append(
        {
            "check_id": mesh_check,
            "semantic_check_id": "semantic:physicsguard-skill-suite-parent:reattach-model-mesh",
            "kind": "command",
            "command": "python",
            "args": [".flowguard/check_physicsguard_skill_suite_mesh.py"],
            "cwd_token": "repository_root",
            "expected": {"exit_code": 0},
            "timeout_seconds": 120,
            "evidence_class": "hard",
            "evidence_domain_id": "physicsguard-skill-suite-parent:model-mesh",
            "execution_owner_id": "owner:physicsguard-skill-suite-parent:reattach-model-mesh",
            "covers_obligation_ids": [mesh_obligation],
            "depends_on_check_ids": child_check_ids,
            "input_selectors": [
                {"kind": "path", "path": ".flowguard/physicsguard_skill_suite_mesh.json"},
                {"kind": "path", "path": ".flowguard/check_physicsguard_skill_suite_mesh.py"},
                {"kind": "path", "path": ".flowguard/physicsguard_suite_parent_inventory.json"},
            ],
            "maintenance_unit_id": PARENT_UNIT_ID,
            "member_skill_id": PARENT_SKILL_ID,
            "evidence_subject_id": (
                "subject:physicsguard-skill-suite-parent:reattach-model-mesh"
            ),
        }
    )
    bindings.append(
        {
            "step_id": "step:physicsguard-skill-suite-parent:reattach-model-mesh",
            "check_ids": [mesh_check],
            "output_artifact_ids": [],
            "action": {
                "kind": "mesh_reattachment",
                "summary": "Verify the existing parent ModelMesh consumes every current child exactly once.",
            },
        }
    )
    implementation_paths = sorted(
        {
            "scripts/verify_physicsguard_suite_parent.py",
            "scripts/verify_guard_simulation_readiness.py",
            ".flowguard/physicsguard_v1_retirement_inventory.json",
            ".flowguard/physicsguard_skill_suite_mesh.json",
            ".flowguard/check_physicsguard_skill_suite_mesh.py",
            ".flowguard/physicsguard_suite_parent_inventory.json",
            *(
                path
                for skill_id in EXPECTED_SKILLS
                for path in (
                    f"skill/{skill_id}/SKILL.md",
                    f"skill/{skill_id}/.skillguard/contract-source.json",
                    f".flowguard/retirement-receipts/{skill_id}.json",
                    f"skill/{skill_id}/guard-model",
                )
            ),
        }
    )
    return {
        "schema_version": "skillguard.contract_source.v2",
        "skill_id": PARENT_SKILL_ID,
        "repository_role": "skill_maintainer_source",
        "maintenance_unit_id": PARENT_UNIT_ID,
        "member_skill_ids": [PARENT_SKILL_ID],
        "consumer_projection": {
            "projection_id": "projection:consumer-distribution",
            "prohibited_path_prefixes": [".skillguard/"],
            "prohibited_prompt_tokens": ["SkillGuard", ".skillguard", "skillguard.py"],
            "release_manifest_path": "consumer-release.json",
        },
        "model_id": model["model_id"],
        "model_path": MODEL_PATH,
        "confirmed": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "checks": checks,
        "artifacts": [],
        "judgment_rubrics": [],
        "closure_profiles": [
            {"profile_id": "enforced", "required_obligation_ids": obligations}
        ],
        "step_bindings": bindings,
        "implementation_paths": implementation_paths,
    }


def main() -> int:
    model = _model()
    source = _source(model)
    CONTROL_ROOT.mkdir(parents=True, exist_ok=True)
    model_text = (
        '"""Generated receipt-only PhysicsGuard parent FlowGuard export."""\n\n'
        "import json\n\n"
        'FLOWGUARD_MODEL_MARKER = "flowguard-executable-model"\n'
        f"EXPORT = json.loads(r'''{json.dumps(model, ensure_ascii=False, separators=(',', ':'))}''')\n\n"
        "def export_contract_model():\n    return EXPORT\n"
    )
    (CONTROL_ROOT / "contract_model.py").write_text(model_text, encoding="utf-8")
    (CONTROL_ROOT / "contract-source.json").write_text(_stable_json(source), encoding="utf-8")
    (PARENT_ROOT / "test-mesh.json").write_text(
        _stable_json(
            {
                "schema_version": "skillguard.test_mesh_manifest.current",
                "mesh_id": "physicsguard-skill-suite-parent.current",
                "source_model_id": model["model_id"],
                "profiles": [
                    {
                        "profile_id": "fast",
                        "closure_profile_id": "enforced",
                        "full_admission_required": False,
                    },
                    {
                        "profile_id": "focused",
                        "closure_profile_id": "enforced",
                        "full_admission_required": False,
                    },
                    {
                        "profile_id": "full",
                        "closure_profile_id": "enforced",
                        "full_admission_required": True,
                    },
                ],
                "claim_boundary": (
                    "Profiles select the same frozen parent owners. Full adds the explicit final-gate "
                    "freeze and does not authorize child execution."
                ),
            }
        ),
        encoding="utf-8",
    )
    print(
        _stable_json(
            {
                "status": "pass",
                "parent_root": PARENT_ROOT.relative_to(ROOT).as_posix(),
                "declared_owner_count": len(EXPECTED_SKILLS) + 1,
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
