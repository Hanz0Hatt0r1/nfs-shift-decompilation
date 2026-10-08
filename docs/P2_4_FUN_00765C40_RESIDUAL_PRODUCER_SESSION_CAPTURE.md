# Process 2 P2.4 — `FUN_00765c40` residual producer session capture

## BLOCKER

`SHIFT.Fun00765c40ExternalPassResult/5` carries an optional `SHIFT.Fun00765c40ResidualProducerHandoff/2`. The active session captures that witness per pass so source-computed residual payloads remain observable before any future composed-executor promotion.

`/2` preserves historical `SHIFT.Fun00765c40ResidualProducerHandoff/1` as its payload prefix and adds per-family presence. The session must preserve that presence information exactly; capturing a witness must not promote absent families or turn them into default producer values.

## OUTPUT

`NativeVehicleProviderSession::execute_explicit_step()` captures the optional producer witness for each of the two recovered physics passes.

The session result exposes:

```text
fun_00765c40_residual_producer_handoffs[2]
```

Each slot is `optional<Fun00765c40ResidualProducerHandoff>` and therefore carries the `/2` `family_presence_explicit` / `family_present[8]` state unchanged.

A dedicated telemetry counter records how many pass results supplied a witness:

```text
fun_00765c40_residual_producer_handoff_capture_count
```

## ORDER

The session preserves the existing active order:

1. call the top-level `FUN_00765c40` provider;
2. validate the typed `/5` result and invariants of producer families declared present;
3. materialize the native authoritative query snapshot;
4. commit query/cache snapshots;
5. capture the optional `/2` producer witness when present;
6. continue the existing `FUN_00766510` / motion-read chain.

## OWNERSHIP

This is diagnostic transport only.

- the witness is **not authoritative**;
- the witness is **not native computation**;
- absence remains valid;
- an absent `/2` family remains absent and is not promoted;
- historical `/1` witnesses remain compatible and mean all eight families are present;
- no producer formula is inferred;
- no `HDVehicle+0x98` owner/lifetime is inferred;
- the session does **not** call `execute_fun_00765c40_composed_residual_pass()`;
- the lower scene-query provider remains external at global `0x00c133ac`, vtable slot `+0x1c0`.

The capture array is local to one `execute_explicit_step()` call. If that step throws later, the local witness capture is discarded with the uncommitted step result; no new persistent rollback state is needed.

## GATE

Complete `FUN_00765c40` internalization remains false. The top-level provider remains present and the external provider count remains **7**.

The remaining explicit producer/owner frontier still contains nine classes. Selective capture and overlay only make it possible to close those classes independently; they do not close any proof by themselves.

## NEXT STEP

As source-backed proofs land, mark only the corresponding `/2` family present and compare it against an independently reconstructed native producer. Only a positively proven family may feed the composed executor; unresolved siblings must remain untouched.
