# Process 2 P2.4 — current `FUN_00765c40` provider frontier

## BLOCKER

The historical `SHIFT.NativeVehicleExternalProviderFrontierCurrent/1` audit is anchored at the Phase726 state. Later P2.4 work changed selected-query ownership, added a composed residual executor, typed the remaining pure-data producer witness, separated producer presence from proof authorization, and internalized the exact machine-visible `FUN_0075cfb0 -> wheel+0x738` store surface.

## OUTPUT

`SHIFT.NativeVehicleExternalProviderFrontierP2_4Current/1` overlays only later positive P2.4 changes while leaving historical evidence untouched.

Current selected-BMW ownership is:

- selected world position: native;
- selected `+0x38e8` miss fallback: native;
- selected typed query input: native;
- session query snapshot: native and authoritative;
- provider-returned selected query input: validation witness only;
- collision output: typed through `SHIFT.Fun00765c40CollisionOutputHandoff/1`;
- composed eleven-stage residual executor: present;
- lower scene-query implementation at global `0x00c133ac`, vtable `+0x1c0`: still external.

The active `Fun00765c40ExternalPassResult` contract is `/5`. It preserves the historical `/4` prefix and carries an optional, non-authoritative `SHIFT.Fun00765c40ResidualProducerHandoff/2`. The `/2` handoff preserves historical `/1` all-family behavior when explicit family presence is disabled.

`SHIFT.Fun00765c40ResidualProducerPromotionGate/1` separates **presence** from **proof authorization**. A present family is not eligible for promotion unless the caller also supplies the matching independent-proof bit. The proof mask defaults to all false, is not itself evidence, and is not wired into the active session. Current authorized-family count is therefore zero.

`SHIFT.Fun0075cfb0LoadStoreSurface/1` now owns the narrower, independently machine-proven wheel-job commit surface: store sites `0x0075d001`, `0x0075ff25`, and `0x0075ff3e`, four `wheel+0x738` destinations, and bit-exact qword transport. This does **not** prove the arithmetic or branch predicates that select/produce those stores.

## REMAINING PRODUCER FRONTIER

The top-level provider cannot yet be removed because the composed executor still requires explicit source-computed or source-owned values for:

- wheel-plane arithmetic;
- the qword source loaded from `HDVehicle+0x98` and copied by `FUN_00752fa0` into each wheel `+0xa00`;
- `FUN_0075cfb0` wheel-job formula and the predicates selecting its proven `+0x738` stores;
- positive-branch / interpolation payloads used by `FUN_007584f0`;
- wheel-pair producer arithmetic;
- contact-array producer arithmetic;
- contact BODY predicates/vectors;
- bounded state-tail predicate/payloads;
- optional BODY sweep predicate/vectors.

`SHIFT.Fun00752fa0WheelStateMachineProof/1` proves the address and exact copy destination for the `HDVehicle+0x98` qword. It does **not** prove a native owner or refresh lifetime for that source field.

No formula or owner in that list is promoted until source or machine evidence proves it. A proven destination/store surface is not equivalent to a proven producer formula.

## GATES

- Process 1 has authorized eventual removal of the top-level `FUN_00765c40` provider after exact end-to-end internalization.
- Complete internalization remains false.
- The top-level provider remains present.
- External provider count remains 7.
- The lower collision provider remains external.
- The `/5` producer witness is optional and non-authoritative.
- `/2` family presence changes transport granularity, not ownership.
- Historical `/1` all-family behavior remains compatible.
- An absent `/2` family cannot default-overwrite an unresolved composed input.
- A present family cannot pass the safe promotion gate without a distinct independent-proof bit.
- No producer family currently has promotion authorization.
- Session capture remains diagnostic and does not call the promotion gate or composed executor.
- The `FUN_0075cfb0` load-store surface is native-owned, but its formula/predicates remain unresolved.

## NEXT STEP

Recover the branch predicates and source arithmetic feeding the three proven `FUN_0075cfb0` `+0x738` stores and independently compare them against native reconstruction. Only after that proof may the WheelJob producer family receive an authorization bit. Provider removal remains fail-closed until the explicit producer list is empty.
