# Process 1 — vehicle RenderHierarchy resource-owner join

## Blocker

`SHIFT.BMWBody0BindFrameProof/1` still needs the final independent relation from the outer Vehicle/root-pose domain to the canonical BMW VHF vehicle-root/frame. Earlier car-body `+0x534` collision and `+0x34` PhysX branches are negative and must not be reused as positive VHF identity evidence.

## Input

Retail `SHIFT.exe` identity is fixed at MD5 `705af8b420e5eb1e3834ac43d5533c6b`. The bounded retail Ghidra C source exposes the selected-vehicle participant, descriptor registry, vehicle render model, resource materializer, explicit `.vhf` loading path, and RenderHierarchy parser family.

The critical source-backed facts are:

- `FUN_004a5800` resolves a vehicle descriptor by a case-insensitive name match against descriptor `+0x10`;
- `FUN_00484720` installs a clone of that registry descriptor at participant `+0xf0` and invokes `FUN_00483c50`;
- `thunk_FUN_00d6e910 -> FUN_004a3000` preserves descriptor `+0x14` and `+0x54`;
- descriptor reflection registers `+0x54` as **`Vehicle Render Model`**;
- `FUN_00483c50` sends the participant descriptor bundle into `FUN_004aecd0` while operating on the embedded participant render model at `+0x1340`;
- `FUN_004aecd0 -> FUN_004aea10` feeds descriptor `+0x14/+0x54` to `FUN_0069c0b0`;
- `FUN_004aea10` materializes loader vslot `+0x24` into render-model `+0x178`;
- `FUN_0043e670` proves that explicit `.vhf` resources use the same `FUN_0069c0b0` loader and the same materialize vslot `+0x24`;
- `FUN_0069c0b9 -> FUN_0069bac0` reaches the parser family whose `FUN_00699b10` grammar explicitly recognizes `HIERARCHY`, `OBJECT`, and `DAMAGE`;
- `FUN_004a8740` consumes the materialized vehicle render object while matching `render\\shaders\\vehicles_basic.fx` and `render\\shaders\\wheels.fx`;
- the same participant has `FUN_004848bc` as its render/root-pose tick and `FUN_00480700` sends `participant+0x1340` to the vehicle world-point consumer `FUN_004a8c20`.

## Output

`tools/ghidra/analyze_vehicle_render_hierarchy_resource_owner.py` emits:

`SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1`

The positive handoff is deliberately limited to:

- selected vehicle registry descriptor -> participant descriptor copy;
- descriptor `+0x54` -> `Vehicle Render Model` semantic identity;
- participant `+0x1340` -> vehicle RenderHierarchy resource owner/materialization path;
- explicit `.vhf` use of the same loader/materialization family;
- vehicle-render-domain confirmation from vehicle/wheel shader consumers.

The report therefore promotes `vehicle_render_hierarchy_owner_ready=true`.

## Remaining BMW-specific edge

This proof **does not** invent the concrete retail value stored in `Vehicle Render Model` for `bmw_m3_e36`.

The next bounded evidence must recover exactly that one descriptor value and join it to the already known canonical BMW VHF resource. Until then the contract intentionally keeps these gates false:

- `selected_BMW_vehicle_render_model_value_ready`;
- `canonical_BMW_VHF_resource_join_ready`;
- `outer_vehicle_root_to_VHF_vehicle_root_ready`;
- `BODY0_bind_frame_proof_ready`;
- `vehicle_world_transform_ready`.

## Usage

```bash
python tools/ghidra/analyze_vehicle_render_hierarchy_resource_owner.py \
  out/shift_ghidra_database \
  /path/to/SHIFT.exe.c \
  --json-out out/vehicle_render_hierarchy_resource_owner_join.json
```

No retail game execution or runtime capture is required for this pass.
