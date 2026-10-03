# Process B — persistent BODY writer closure

Process B originally froze `SHIFT.BodyPersistentStateABI/1` with four unresolved
persistent lanes: `origin`, `cross_vector`, `motion_triplet`, and `basis`.
That boundary was correct for the evidence available at the time, but it is now
historical.

Process A subsequently established `SHIFT.BodyFrameIntegrationStatic/1` from the
recovered retail source plus matching x86 bytes.  The closed Process B view is
published as `SHIFT.BodyPersistentStateABI/2` in
`src/physics/body_persistent_state_abi_v2.py`.

No game execution or runtime capture is required for this closure.

## Proven writer path

The direct/static chain is:

```text
FUN_00770e80
  -> FUN_0076d100
  -> FUN_00765470(0.5 * dt)
       -> FUN_00763570
       -> FUN_007b3f40
       -> FUN_007b4110
       -> FUN_007b2270
            -> FUN_007bab70
  -> FUN_007b8810
  -> FUN_0076d100
  -> FUN_00765470(0.5 * dt)
       -> same solve/post-solve/integration order
  -> FUN_007b8810
```

`FUN_007b2270` iterates the BODY array at owner `+0x14`, using owner `+0x10`
as the count and `0x170` as the BODY stride.  Every element receives the same
f64 timestep and is passed to `FUN_007bab70`.

## Closed persistent lanes

`FUN_007bab70` proves the previously missing state transitions:

```text
origin += motion_triplet * dt
motion_triplet += accumulator_b * BODY[+0x90] * dt
prepared_vector += accumulator_a * dt
cross_vector = symmetric_tensor * prepared_vector
basis = rotate(basis, cross_vector * dt)
```

Therefore the persistent graph is continuous across:

```text
+0x60..+0x70 -> +0x78..+0x88 -> +0x00..+0x10
+0x48..+0x58 -> +0x30..+0x40 -> +0x18..+0x28 -> +0xd4..+0xf4
```

The physical unit/name of BODY `+0x90` remains intentionally unpromoted; only
its multiplicative role is proven.

## Relationship to the broad p-code bridge sieve

The earlier `SHIFT.BodyWriterBridgeCandidates/1` workflow remains useful as a
fail-closed target-selection layer, but it must not be treated as object identity.
A same-register/same-offset pattern can be a false positive when a long function
reuses a register for unrelated pointers, when the base is the stack frame, or
when a vtable/count/array field happens to share a BODY displacement.

The persistent writer no longer needs to be inferred from that broad sieve:
`FUN_007bab70` is source- and retail-machine-code-backed directly.

## Compatibility

`body_persistent_state_abi_runtime.py` and
`SHIFT.BodyPersistentStateABI/1` are retained unchanged for consumers that need
the historical fail-closed frontier.  New work that needs the closed persistent
writer graph should use `body_persistent_state_abi_v2.py`.

In v2:

- `unresolved_persistent_lanes()` is empty;
- `writers_for_offset()` reports `FUN_007bab70` for origin, cross-vector,
  prepared-vector, motion-triplet, and basis destinations;
- `native_pose_handoff()["ready"]` is `True` for a source-backed integrator/oracle
  and native-port handoff;
- higher-level input/control ownership, retail semantic names, BODY `+0x90`
  physical naming, and rendered-frame cadence remain explicit unknowns.
