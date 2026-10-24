# physics-model-deepening Specification

## Purpose
Compare declared model-derived device variants, request a discriminating next measurement, and report when the observations exceed the declared alternatives.

## Requirements
### Requirement: Competing causes are model-derived variants
Competing causes SHALL be declared as `fault_variants` in the audit tree and evaluated by the native variant engine. Evaluation SHALL copy device data, rederive declared outcomes, and check them against the unchanged nominal model; it SHALL NOT optimize observations or claim the true physical cause.

### Requirement: Next signals follow bounded separation evidence
`hierarchy variants` SHALL return `pairwise` checked-signature or scale-normalized unmeasured-signal separation and rank `next_signal` by the number of same-signature pairs separated, then normalized separation. Unavailable cases SHALL retain reasons and SHALL NOT create discrimination evidence. Physically masked pairs SHALL stay visible; undetected or outside-expected pairs SHALL fail.

### Requirement: Observations return matches or a model miss
With `--observed`, the report SHALL compare the observed checked signature with evaluated fault variants and return `matching_variants`. A failed observed audit with no match SHALL set `model_miss: true` and exit 1; a healthy observed audit SHALL NOT be a model miss. Without observations, `model_miss` SHALL be null.
