# Process 2 P2.4 — current `FUN_00765c40` provider frontier

## BLOCKER

The historical `SHIFT.NativeVehicleExternalProviderFrontierCurrent/1` audit is anchored at the Phase726 state. Later P2.4 work changed selected-query ownership and added a composed residual executor, so treating the Phase726 description as current now misstates the runtime boundary.

## OUTPUT

`SHIFT.NativeVehicleExternalProviderFrontierP2_4Current/1` overlays only the later positive P2.4 changes while leaving the historical audit untouched.

Current selected-BMW ownership is:

- selected world position: native;
- selected `+0x38e8` miss fallback: native;
- selected typed query input: native;
- session query snapshot: native and authoritative;
- provider-returned selected query input: validation witness only, not authoritative session state;
- collision output: typed through `SHIFT.Fun00765c40CollisionOutputHandoff/1`;
- composed eleven-stage residual executor: present;
- lower scene-query implementation at global `0x00c133ac`, vtable `+0x1c0`: still external.

The active `Fun00765c40ExternalPassResult` contract is `/4`, not the historical `/2` recorded by the Phase726 audit.

## REMAINING PRODUCER FRONTIER

The top-level provider cannot yet be removed because the composed executor still requires explicit source-computed or source-owned values for:

- wheel-plane arithmetic;
- the qword source loaded from `HDVehicle+0x98` and copied by `FUN_00752fa0` into each wheel `+0xa00`;
- `FUN_0075cfb0` wheel-job formula;
- positive-branch / interpolation payloads used by `FUN_007584f0`;
- wheel-pair producer arithmetic;
- contact-array producer arithmetic;
- contact BODY predicates/vectors;
- bounded state-tail predicate/payloads;
- optional BODY sweep predicate/vectors.

`SHIFT.Fun00752fa0WheelStateMachineProof/1` proves the address and exact copy destination for the `HDVehicle+0x98` qword. It does **not** prove a native owner or refresh lifetime for that source field, so the composed executor's `wheel_state_source_bits` remains a real explicit dependency rather than a native-owned value.

No formula or owner in that list is promoted until source or machine evidence proves it.

## GATES

- Process 1 has authorized eventual removal of the top-level `FUN_00765c40` provider after exact end-to-end internalization.
- Complete internalization remains false.
- The top-level provider remains present.
- External provider count remains 7.
- The lower collision provider is not renamed or semantically inferred.

## NEXT STEP

Trace ownership/refresh lifetime for `HDVehicle+0x98`, or recover one remaining explicit producer formula from pinned PC-retail evidence, then consume it in `SHIFT.Fun00765c40ComposedResidualExecutor/1`. Provider removal remains fail-closed until the explicit producer list is empty.
