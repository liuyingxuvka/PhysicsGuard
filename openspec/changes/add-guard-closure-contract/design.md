## Overview

Add a skill-level closure helper that wraps `physicsguard.cli hierarchy evaluate/plan` and inspects audit result fields.

## Design

- Missing audit or observed snapshot creates partial closure.
- `audit_pass=false` or missing required variables/parameters blocks completion.
- Recommended refinements and bug-family followups remain next actions.
- Changed observed snapshots stale prior evidence.

## Risks

- The helper does not add high-fidelity solvers or automatic repair.
- It only routes low-fidelity audit evidence and AI debugging next steps.
