# Read the given numbers from the question

This small illustrative shower question checks a heat balance and a mixing balance. It is a pointwise check, not a stateful simulation or an external physical reference.

```sh
python -m physicsguard.cli hierarchy evaluate examples/source_reading/audit.yaml examples/source_reading/observed.yaml
python -m physicsguard.cli hierarchy evaluate examples/source_reading/audit.yaml examples/source_reading/observed_bad.yaml
```

The first command exits 0; the second exits 1 and names the forgotten `/60` as `source_reading_disagrees` with `x60`. `observed.yaml` shows both exact text quotes and a table-cell quote:

```yaml
sources: {question: question.txt}
properties:
  water_density:
    value: 1.0
    unit: kg/L
    quote: {from: question, text: 'water: 1 kg/L'}
parameters:
  heater.cp_J_kgK:
    unit: J/kg/K
    quote: {from: question, text: 'cp 4186 J/kg/K'}
variables:
  heater.m_dot_kg_s:
    value: 0.1
    unit: kg/s
    quote: {from: question, row: Hot, column: Flow}
  heater.T_in_K:
    value: 288.15
    unit: K
    quote: {from: question, text: 'from 15 C'}
```

The complete files include the other required quantities. Readings are taken from the matching original span, converted through the sole unit table and compared with the AI's value. A quoted parameter replaces the audit parameter. Quote one number and unit, or one range: `6 to 7 L/min` checks that the chosen value lies inside. Unreadable numbers, ambiguous grouping and unquoted inputs stay grey. Source rows and file hashes are in JSON `metadata.source_readings` and `metadata.sources`; the text and quantity-flow picture consume the same report. A physical pass with only AI values remains grey.

For the existing CSV example, select by a key rather than a guessed row:

```sh
python -m physicsguard.cli testfile snapshot examples/hierarchical/heated_tank/tank_run_contract.yaml --at time_s=700 --out measured.yaml
```

The snapshot records `row_key: {file: tank_run.csv, field: time_s, value: 700}`. An observation can instead give that key's `quote: {from: question, text: 'at t = 700 s'}` under `row_key` when the question states it. CSV units come from the header; generated snapshots retain raw values and units without stored conversion factors. A snapshot without a key says that the AI chose the row. An explicitly calibrated transducer remains unchecked, even if its column name suggests a physical unit.

Known boundary: equal numeric readings can still be attached to the wrong semantic roles; number words, midnight clock spans and complex non-pipe tables are not inferred. The report does not license a claim outside the equations and quoted spans it checked.
