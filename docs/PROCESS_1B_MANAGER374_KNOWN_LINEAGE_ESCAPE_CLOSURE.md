# Process 1B — Participants Manager known-lineage escape closure

## Result

This contract closes one narrower question than the global opaque-runtime blocker:

> Can the known canonical Participants Manager root lineage leak the exact root into memory or an external call and later re-enter as an apparently unrelated `manager+0x374` writer source?

For the merged PC retail 1.02 evidence, the answer is **no** for the known lineage.

## Exact-root propagation

`FUN_00489ad0()` returns the exact Participants Manager singleton root `0x00bc9fc0`.

The merged exact-root alias contract covers 394 direct getter callsites and reports:

- 0 exact-root object/global stores;
- 9 stack saves, all bounded by the completed stack-local/stack-argument alias analysis;
- 0 immediate `push eax` after the getter;
- escaped-storage surface complete;
- stack-argument alias surface complete.

Therefore the canonical getter lineage does not seed an arbitrary object/global memory copy of the exact manager root and does not export it through the audited stack-argument paths.

## Direct callees

The exact-root direct-thiscall surface contains 9 targets. All nine resolve to code inside the retail image. No external/import target is present in that finite surface.

Only `FUN_00d60660` writes `manager+0x374`, and its stored value is the selected allocator-owned `manager+0x2a0` entry, already rejected as fixed `HDVehicle+0x4330` identity.

## Setter surfaces

The older full-retail setter inventory remains useful as a separate cross-check:

- 44 direct manager-receiver calls;
- 12 unique direct targets;
- 18 manager vtable slots;
- 17 unique vtable targets;
- no direct `manager+0x374` setter in either surface.

The newer Participants lifecycle closure additionally resolves the escaped `manager+0x20` lifecycle path, including six indirect calls from vtable `+0x0c`; that surface does not recover the parent root into a nonzero `manager+0x374` writer.

## Adjudication

The following bounded gates are now true:

```text
known_manager_root_lineage_escape_surface_complete = true
known_manager_root_lineage_can_seed_external_memory_alias = false
known_manager_root_lineage_reaches_external_direct_callee = false
known_manager_root_lineage_helper_or_indirect_setter_surface_complete = true
```

This does **not** close arbitrary process memory or an independent opaque computation that somehow synthesizes the exact absolute root `0x00bc9fc0` without first receiving the known canonical root lineage.

Accordingly these global gates remain fail-closed:

```text
independent_opaque_or_external_runtime_root_synthesis_complete = false
global_manager_root_origin_surface_complete = false
global_helper_non_vtable_indirect_setter_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
provider count = 7
```

## Next step

Reduce the remaining independent opaque/external synthesis class to concrete machine candidates. Only after that class is either exhausted or shown unable to reach another `manager+0x374` writer should Process 1B perform the final slot2 identity adjudication.
