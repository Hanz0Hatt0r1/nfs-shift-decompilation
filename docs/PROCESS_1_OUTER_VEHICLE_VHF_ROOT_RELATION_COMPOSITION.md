# Process 1 — outer Vehicle / BMW VHF root relation composition

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`SHIFT.BMWBody0BindFrameProof/1` is still blocked by the exact outer Vehicle-root
-> canonical BMW VHF `HIERARCHY Root` relation.

PR #1330 / `SHIFT.VehicleRenderModelRootAffineDomainJoin/1` closed the missing
ownership/coordinate-domain edge: the participant root affine is now proven to be
the local-to-world affine for coordinates owned by the same materialized Vehicle
Render Model selected as canonical `vehicles/bmw_m3_e36/bmw_m3_e36.vhf`.

The remaining work is therefore no longer an owner search. It is exact affine
composition plus numeric materialization of the already-bounded
`FUN_00795d60` setup delta.

## INPUT

This stage consumes four already-defined Process 1 contracts:

```text
SHIFT.VehicleRenderModelRootAffineDomainJoin/1
SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
SHIFT.BMWVHFHierarchyRootFrame/1
```

The subject is fixed to the exact canonical BMW VHF decoded SHA-256:

```text
e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51
```

The bridge already proves:

```text
P_render = P_outer + R_outer * delta_local

delta_local =
  outerVehicle+0x19c
  outerVehicle+0x1a0
  outerVehicle+0x1a4
```

and the delta-provenance contract proves exact entry-ECX STORE/value-root
coverage for those three fields in `FUN_00795d60`.

## OUTPUT

New fail-closed composition contract:

```text
SHIFT.OuterVehicleVHFRootRelationComposition/1
```

implemented by:

```text
tools/ghidra/build_outer_vehicle_vhf_root_relation_composition.py
```

It proves the exact matrix multiplication order without inventing the missing
numeric delta.

For D3D/SVWT row-vector affine matrices:

```text
M_render_world = T_row(delta_local) * M_outer_world

M_vhf_root_world = M_vhf_root_model * M_render_world
                 = M_vhf_root_model
                   * T_row(delta_local)
                   * M_outer_world
```

Therefore the two local-frame directions are:

```text
VHF root local -> outer Vehicle local:
  M_vhf_to_outer = M_vhf_root_model * T_row(delta_local)

outer Vehicle local -> VHF root local:
  M_outer_to_vhf = T_row(-delta_local) * inverse(M_vhf_root_model)
```

The builder validates the exact VHF Root row matrix and computes its affine
inverse. This is deliberately useful even when the VHF Root matrix is not
identity.

## GATES_CHANGED

New narrow gate:

```text
outer_vehicle_to_VHF_root_fixed_affine_formula_ready = true
```

The existing semantic/numeric admission gates remain fail-closed:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
outer_vehicle_root_to_VHF_numeric_matrix_ready       = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

The distinction is intentional. The formula and multiplication direction are no
longer blockers; the exact BMW numeric `delta_local` still is.

## NUMERIC FRONTIER

The next proof is now exactly:

```text
source-backed BMW numeric values for
FUN_00795d60 -> outerVehicle+0x19c/+0x1a0/+0x1a4
```

followed by direct evaluation of:

```text
T_row(-delta_local) * inverse(M_vhf_root_model)
```

Existing retail resource evidence already proves that the CDF `GraphicalOffset`
source field maps to load-data offsets `+0xd0/+0xe4/+0xf8` and is exactly
`[0, 0, 0]` for BMW. That fact is useful for the next numeric pass, but this
composition stage does not incorrectly conclude that the final setup delta is
zero: `FUN_007c3b00`/`FUN_00795d60` perform additional source-backed setup
arithmetic and geometry-centering before the final stores.

## LIMITS

This stage does **not**:

- infer outer/VHF identity from an identity-valued VHF root matrix;
- guess `FUN_00795d60` numeric delta values;
- treat CDF `GraphicalOffset == 0` as proof that the final delta is zero;
- use visual alignment or host runtime output as frame evidence;
- promote `SHIFT.BMWBody0BindFrameProof/1`;
- require original-game execution or a new runtime capture.

The current `/1` delta-provenance schema explicitly carries
`numeric_delta_value_proven=false`; if those fields somehow become true inside
that same frontier, the composition builder rejects the input and requires a new
explicit numeric producer contract instead of silently changing proof semantics.

## TESTS

`tests/test_ghidra_outer_vehicle_vhf_root_relation_composition.py` covers:

- positive non-identity VHF root composition and exact inverse order;
- identity-valued VHF root without semantic promotion;
- upstream relation preclaim rejection;
- incomplete `FUN_00795d60` delta STORE coverage rejection;
- non-affine VHF root matrix rejection;
- rejection of accidental numeric promotion inside the non-numeric `/1` delta
  provenance frontier.

## NEXT_OWNER

Process 1: materialize the exact BMW numeric `FUN_00795d60` delta from the
already-bounded setup/resource chain. Then evaluate the frozen formula above,
publish the exact outer Vehicle -> VHF root matrix, compose the already-positive
BODY0 -> outer Vehicle matrix, and assemble `SHIFT.BMWBody0BindFrameProof/1`.
