# Process 2 — provider and identity frontier refresh after Phase 706

## Playable-slice blocker reduced

This refresh keeps the Phase 699/701 external-provider graph aligned with the
current cross-process contracts. It adds no physics arithmetic and no new
numbered phase.

The important closed or narrowed boundaries now are:

```text
Process 1 #1196  SHIFT.GlobalVehicleBodyOwnerIdentity/1 composition
Process 2 703    composed BODY-owner identity consumer
Process 1 #1199  exact BODY0/VHF composition equation
Process 1 #1200  finite BODY0 bind-initialization static worklist
Process 2 704    native BODY0/VHF world-matrix composition
Process 2 705    NativeRuntimeState -> VehicleWorldMatrix handoff
Process 2 706    persistent freshness-checked BMW vehicle transform
Process 3 645    exact BMW VHF static bind transform + VHF->SVWT convention
Process 3 646    dynamic vehicle transform transport core + exact vehicle draw identity
```

The graph must therefore stop requesting either the obsolete update-child
pointer-equality proof or the already-closed BODY0/VHF composition itself.

## Provider result

The deepest Phase 697 path, wrapped by the persistent Phase 701 provider session,
still has exactly nine external provider boundaries:

```text
external_provider_count = 9
implement_now            = 0
request_process1         = 9
runtime_only_blocked     = 0
```

No new Process 1 result proves a complete provider strongly enough to replace
one of these nine boundaries. Integration depth must not be faked by host math,
guessed control state, partial kernels, or transform work that does not close a
provider producer.

## Current vehicle/BODY identity boundary

The authoritative identity model remains:

```text
SHIFT.GlobalVehicleBodyOwnerIdentity/1
```

Phase 703 consumes it directly and reuses the Phase 698 selector plus Phase 700
runtime pose handoff. The historical update-child equality condition remains
explicitly unnecessary.

Current retail admission is still blocked because the targeted retail
`SHIFT.GhidraFunctionInstructions/2` export for `FUN_00765470` is not committed,
so Process 1 cannot yet prove entry ECX reaches `FUN_007b2270` as BODY-array
owner ECX on all required paths.

That finite receiver-provenance proof is the identity request. A new vehicle-base
identity search is not.

## FUN_00765470 provider semantics remain separate

Closing BODY-owner receiver identity does not implement
`Fun00765470MachineScalarHalfStepProvider`. The provider still needs exact
source-backed field producers and exact refresh/reuse ordering across the two
half-steps.

The frontier therefore keeps receiver identity and composite producer scheduling
as separate blockers.

## Vehicle world-transform chain after Phases 704–706

The semantic composition formula is no longer open. Process 1 #1199 proves:

```text
M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime
```

with the recovered BODY basis converted into the established D3D row-vector
convention. Process 2 now carries that proof through:

```text
Phase 704  exact native composition, fail-closed on bind witness
Phase 705  admitted NativeRuntimeState BODY0 pose -> VehicleWorldMatrix
Phase 706  transactional persistent transform + stale-source rejection
```

Process 1 #1200 narrows the missing bind witness to a deterministic static
caller/callsite worklist but explicitly keeps `BODY0_bind_matrix_proven=false`.
Therefore the remaining semantic transform request is only:

```text
positive SHIFT.BMWBody0BindFrameProof/1
with source-backed BODY0-local -> VHF-vehicle-root bind matrix
```

The current retail world matrix stays false until both that bind witness and the
separate global BODY-owner identity are positive.

## Renderer side

Process 3 Phase 645 supplies the canonical VHF static bind transform. Phase 646
supplies exact vehicle draw-group identity and a non-cumulative native dynamic
transform core.

After a current Phase 706 transform exists, the renderer-side follow-up is
mechanical live Vulkan vehicle-buffer wiring. That work must not be mistaken for
a BODY-frame proof, and Phase 706 itself does not mutate renderer state.

## Other remaining joins

These remain unchanged and fail-closed:

- exact outer-update cadence owner; explicit outer update must not be silently
  attached to `fixed_step()`;
- retail resources -> concrete initial `0x170` BODY records;
- all machine-scalar sqrt/trig/x87 boundaries in Phase 692;
- complete producers for the remaining external provider rows;
- `FUN_00765470` field ownership and refresh/reuse scheduling even after its
  receiver identity closes.

## Safety / parity

The refreshed frontier preserves:

- two half-steps and recovered ordering;
- persistent BODY bytes and typed snapshots;
- participant admission before side effects;
- missing-provider fail-closed behavior;
- no host `sqrt/sin/cos` substitution;
- no update-child pointer equality requirement;
- no promotion of the Phase 645 static VHF bind transform as BODY0 pose;
- no treatment of Phase 704 as a retail BODY0 bind proof;
- no treatment of Phase 706 persistence as renderer mutation;
- no automatic fixed-step transform commit;
- no original `SHIFT.exe` execution and no new runtime capture.

## Next Process 2 action

There is still no source-backed external provider that can be replaced
immediately. Process 2 should consume the first new positive Process 1 proof.
The two highest-impact upstream facts are now explicit and independent:

```text
1. FUN_00765470 entry-ECX -> BODY-array-owner receiver provenance
   -> makes SHIFT.GlobalVehicleBodyOwnerIdentity/1 retail-positive

2. source-backed BODY0 bind matrix
   -> makes SHIFT.BMWBody0BindFrameProof/1 positive
```

Once both are positive, Phases 703/700/704/705/706 already provide the native
path from persistent BODY0 state to a current vehicle world matrix. Process 3
can then consume that matrix through Phase 646 and its live Vulkan wiring without
inventing another transform convention.
