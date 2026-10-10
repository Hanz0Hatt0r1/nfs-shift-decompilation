# Process 1B — render-manager live exact-root call-boundary closure

This contract composes the already merged canonical-root propagation evidence at the point where an exact `DAT_00bc185c` render-manager alias is live across a machine call boundary.

## Inputs

- `SHIFT.P1B.RenderManagerCanonicalAccessClosure/1`
- `SHIFT.HDVehicle64e8RenderManagerMachineCfgCallBoundaryReconciliation/1`
- `SHIFT.HDVehicle64e8Manager374VSlot0cDispatchClosure/1`
- `SHIFT.P1B.RenderManagerBoundedCalleeClosure/1`

## Machine-wide call-boundary inventory

The cross-block replay observes:

- 303 exact-root call-boundary observations;
- 302 unique callsites;
- 207 callsites where only callee-saved exact aliases remain live;
- 95 callsites with an exact alias in caller-saved state;
- 92 direct callsites;
- exactly 3 indirect callsites;
- 41 EAX-only callsites, retained only as residue evidence;
- 54 ECX/EDX receiver-like callsites, 51 of them direct.

The three indirect callsites are exactly:

```text
0x0056bcf2 -> vslot +0x1c
0x0056bd09 -> vslot +0x20
0x0056bd59 -> vslot +0x1c
```

The independent vslot closure proves that these are the complete exact-manager first-hop indirect receiver transfers and that target slot `+0x0c` is reached zero times. Therefore the canonical-lineage live-root machine surface contains **zero non-vtable indirect callsites**.

## Direct callees

The separately merged bounded direct-callee closure already proves 17/17 direct receiver targets closed with zero remaining targets. The two address-of-stack-local helper handoffs are included there and are closed-negative because the pointed local is overwritten before the original exact root can be observed.

## Scoped adjudication

`SHIFT.P1B.RenderManagerLiveCallBoundaryClosure/1` promotes only the bounded canonical-lineage statement:

```text
canonical_lineage_live_call_boundary_surface_complete = true
all_live_exact_root_indirect_calls_classified = true
canonical_lineage_live_exact_root_non_vtable_indirect_setter_surface_complete = true
canonical_lineage_live_exact_root_non_vtable_indirect_setter_found = false
```

This is enough to stop reopening a hypothetical non-vtable setter reached while the known canonical root is already live.

It deliberately does **not** promote the global gates:

```text
helper_non_vtable_setter_surface_complete = false
opaque_helper_created_exact_root_surface_complete = false
arbitrary_unknown_memory_exact_root_alias_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
```

An opaque helper could still synthesize or return the exact numerical pointer from unrelated unknown input, and unrelated memory could theoretically contain the same pointer without a canonical-lineage transfer visible to this replay. Those classes remain the next Process 1B frontier.

No object identity is inferred from equal numeric offsets. Provider count remains 7.
