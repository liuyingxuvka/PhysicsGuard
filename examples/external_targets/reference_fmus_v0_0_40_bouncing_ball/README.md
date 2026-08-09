# Reference-FMUs v0.0.40 BouncingBall target DNA

This directory preserves the reusable, human-readable PhysicsGuard model for the independently maintained Modelica Association Reference-FMUs BouncingBall FMI 3.0 target. It contains no third-party ZIP, FMU, DLL, extracted source, documentation, or generated portable bundle.

The four canonical descriptors are:

- `fmi_observation_request.yaml`: exact official source/release/license identities, content hashes, FMI members and variables, restricted independent oracles, and five executable behavior cases.
- `target_material.json`: the complete 61-member observed target denominator used by the current target-inventory adapter.
- `target_inventory_authority.yaml`: the frozen inventory owner and terminal receipt expected from those exact target-material bytes.
- `physical_blueprint.yaml`: the parent/child physical model, typed input/output/state/effect interfaces, semantics, validity boundaries, refinements, code/test/oracle/evidence bindings, and case results.

The official upstream is `https://github.com/modelica/Reference-FMUs`, release `v0.0.40`, under BSD-2-Clause. The exact release ZIP SHA-256 is `6efe688afe1b2802fe0f011259788396a370f78f2f115b7897285503a884741c`; the exact FMI 3.0 BouncingBall FMU SHA-256 is `4b6c1034f644122e10faa346b2c44549d8634d427a32a28eebcf0d893a66efec`. Every remaining required byte identity and relative locator is frozen in `fmi_observation_request.yaml`.

The model deliberately declares `artifact_root: explicit_material_root`. A normal review therefore does not search the repository, download files, or silently reuse nearby bytes:

```text
python -m physicsguard.cli blueprint review examples/external_targets/reference_fmus_v0_0_40_bouncing_ball/physical_blueprint.yaml --target-authority examples/external_targets/reference_fmus_v0_0_40_bouncing_ball/target_inventory_authority.yaml --pretty
```

Without a separately supplied root, the first gap is `external_resource_not_run`. To execute the qualification, prepare a material directory that exactly matches the relative paths and hashes in the observation request, including copies of `fmi_observation_request.yaml` and `target_material.json`, then name that directory explicitly:

```text
python -m physicsguard.cli blueprint review examples/external_targets/reference_fmus_v0_0_40_bouncing_ball/physical_blueprint.yaml --target-authority examples/external_targets/reference_fmus_v0_0_40_bouncing_ball/target_inventory_authority.yaml --material-root <EXACT_MATERIAL_ROOT> --pretty
```

A passing live review licenses only static closure and the exact replayed cases for the frozen bytes. The portable bundle is generated outside this directory. A bundle-only consumer can inspect hierarchy, contracts, cases, impact, reverse traces, hashes, and frozen observed values, but its execution status remains `observed_at_export_unlicensed`: the bundle does not contain the FMU bytes or a trusted signed execution receipt and therefore cannot claim that it freshly executed the model.
