# Process 2 P2.4 — `FUN_00765c40` residual producer session capture

## BLOCKER

`SHIFT.Fun00765c40ExternalPassResult/5` can now carry an optional `SHIFT.Fun00765c40ResidualProducerHandoff/1`, but the active session previously discarded that witness immediately after the provider returned.

That made the typed `/5` transport incomplete: a provider could expose source-computed residual payloads, but Process 2 had no per-pass observation point for validating them before any future composed-executor handoff.

## OUTPUT

`NativeVehicleProviderSession::execute_explicit_step()` now captures the optional producer witness for each of the two recovered physics passes.

The session result exposes:

```text
fun_00765c40_residual_producer_handoffs[2]
```

Each slot is `optional<Fun00765c40ResidualProducerHandoff>`.

A dedicated telemetry counter records how many pass results actually supplied a witness:

```text
fun_00765c40_residual_producer_handoff_capture_count
```

## ORDER

The session preserves the existing active order:

1. call the top-level `FUN_00765c40` provider;
2. validate the typed `/5` result;
3. materialize the native authoritative query snapshot;
4. commit query/cache snapshots;
5. capture the optional producer witness when present;
6. continue the existing `FUN_00766510` / motion-read chain.

## OWNERSHIP

This is diagnostic transport only.

- the witness is **not authoritative**;
- the witness is **not native computation**;
- absence remains valid;
- no producer formula is inferred;
- no `HDVehicle+0x98` owner/lifetime is inferred;
- the session does **not** call `execute_fun_00765c40_composed_residual_pass()`;
- the lower scene-query provider remains external at global `0x00c133ac`, vtable slot `+0x1c0`.

The capture array is local to one `execute_explicit_step()` call. If that step throws later, the local witness capture is discarded with the uncommitted step result; no new persistent rollback state is needed.

## GATE

Complete `FUN_00765c40` internalization remains false. The top-level provider remains present and the external provider count remains **7**.

The remaining explicit producer/owner frontier still contains nine classes. Capturing their values does not close any of those ownership proofs.

## NEXT STEP

Use source-backed selected-provider production to populate one or more witness fields and compare those captured values against native reconstruction. Only after a producer is independently proven should the session allow that field to feed the composed executor.
