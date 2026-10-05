# Process 1 — BMW `Vehicle Render Model` -> canonical VHF resource join

## Blocker removed

**Which concrete blocker of the first playable Linux vertical slice does this work remove?**

The previous `SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1` proof established
that selected vehicle descriptor `+0x54` is the retail **`Vehicle Render Model`**
field and that it feeds the same RenderHierarchy loader/materialization family
used by explicit `.vhf` resources. It intentionally left the concrete
`bmw_m3_e36` field value unknown.

This pass closes exactly that BMW-specific resource identity edge.

## Retail resource evidence

The retail BMW descriptor exists byte-identically in three supplied archives:

```text
VehiclesGlobal.bff      entry 32
VehiclesPersistent.bff  entry 27
BMW_M3_E36.bff           entry 1121
```

All three decode to SHA-256:

```text
9dd97be4767c2d96782801a4555ac0581b4cff65432635a11d456b39cf35352b
```

The selected reflection object is:

```xml
<data class="VehicleDetails" id="0x2A6C460">
    <prop name="Name" data="BMW_M3_E36" />
    ...
    <prop name="Vehicle Render Model" data="BMW_M3_E36.vhf" />
</data>
```

Therefore the exact retail value previously missing from the static owner proof
is:

```text
Vehicle Render Model = BMW_M3_E36.vhf
```

No basename guess is needed. Resolving that relative resource value against the
BMW descriptor resource directory gives:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

The primary retail `BMW_M3_E36.bff` contains exactly one entry at that logical
path:

```text
entry_index        1083
compression_type   2
compressed_size    4914
uncompressed_size  88599
decoded_sha256     e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51
```

The decoded resource independently identifies itself as:

```xml
<CAR Name="BMW_M3_E36" ...>
    <NODE type="HIERARCHY" Name="Root" MatrixNumber="0" ...>
```

The cockpit archive does not collide with this identity: its VHF path is
`vehicles/bmw_m3_e36/bmw_m3_e36_cockpit.vhf`.

## Machine-readable handoff

`tools/ghidra/build_bmw_vehicle_render_model_resource_join.py` emits:

```text
SHIFT.BMWVehicleRenderModelResourceJoin/1
```

and makes these gates positive:

```text
selected_BMW_vehicle_render_model_value_ready = true
canonical_BMW_VHF_resource_join_ready          = true
```

The checked retail evidence is recorded in:

```text
evidence/process1_bmw_vehicle_render_model_resource_join.json
```

## Remaining boundary

Resource identity is not coordinate-frame equivalence. This pass therefore
keeps these gates closed:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                  = false
vehicle_world_transform_ready                 = false
```

The next shortest frontier is now narrower: join the already-proven outer/root-
pose transport to the **exact** BMW VHF `HIERARCHY` root and prove the root-frame
relation. Do not reopen the rejected car-body `+0x34/+0x534` or render-manager
`+0xca4` branches.

## Reproduction

Given the positive owner proof and the retail archives:

```bash
python tools/ghidra/build_bmw_vehicle_render_model_resource_join.py \
  out/vehicle_render_hierarchy_resource_owner_join.json \
  /path/to/BMW_M3_E36.bff \
  /path/to/VehiclesGlobal.bff \
  /path/to/VehiclesPersistent.bff \
  /path/to/BMW_M3_E36.bff \
  --json-out out/bmw_vehicle_render_model_resource_join.json
```

No original-game execution or new runtime capture is required.
