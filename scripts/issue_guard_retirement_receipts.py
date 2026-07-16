"""Issue deterministic expanded-scope V1 retirement receipts for all maintained skills."""

from __future__ import annotations

import json
from pathlib import Path

from verify_guard_simulation_readiness import (
    SKILLS,
    retirement_receipt_path,
    write_retirement_receipt,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    receipts = []
    for target_skill_id, source_relative, _installed_name in SKILLS:
        receipt = write_retirement_receipt(
            ROOT / source_relative,
            target_skill_id,
            retirement_receipt_path(target_skill_id),
        )
        receipts.append(
            {
                "target_skill_id": target_skill_id,
                "receipt_id": receipt["receipt_id"],
                "receipt_hash": receipt["receipt_hash"],
            }
        )
    print(
        json.dumps(
            {
                "artifact_kind": "physicsguard_v1_retirement_receipt_issuance",
                "status": "pass",
                "receipt_count": len(receipts),
                "receipts": receipts,
                "claim_boundary": (
                    "Issuance proves only the source-side expanded residual scan and exact "
                    "current authority hashes. Installation and parent closure remain separate gates."
                ),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
