# S5 — retail outer-update cadence admission

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`retail-outer-update-scheduler-cadence-admission`: continuous native BMW physics
must consume the retail outer-update scheduler instead of treating the host
`1/60` loop as retail evidence.

## INPUT

The proof joins pinned static views of the same retail executable:

- `SHIFT.exe.c` SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`;
- `SHIFT.exe` MD5 `705af8b420e5eb1e3834ac43d5533c6b`;
- `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`;
- positive `SHIFT.PhysicsManagerSchedulerEntryOwner/1` proving cPhysicsManager
  vtable slot `+0x18 -> FUN_00711b50`;
- exact retail PE byte windows covering registration, controller-list transport,
  BManager dispatch selection, scheduler argument forwarding, accumulator update,
  and `+0x388` rate consumption.

No original-game execution or runtime capture is used.

## OUTPUT

`evidence/s5_retail_outer_update_cadence.json` publishes
`SHIFT.RetailOuterUpdateCadence/1` with `retail_cadence_admitted=true` for the
**default BManager mode** (`+0x529 == 0`).

The corrected registration/dispatch chain is:

```text
FUN_0070fe90()
  -> source-backed DAT_00c104e0 cPhysicsManager
  -> FUN_006485b0 with manager in ECX/this
  -> FUN_00662600
  -> controller +0x58 list, manager stored at node +0x0c
  -> FUN_006626a0 when controller state == 6
  -> FUN_0065b8b0
  -> FUN_00647ef0 per-manager timing gate
  -> FUN_00647d80
  -> default mode vtable +0x18
  -> FUN_00711b50
  -> already-proven direct scheduler chain
```

This corrects two earlier frontier assumptions:

- `FUN_00647da0` dispatches vtable `+0x20`, not `+0x18`;
- `FUN_0070fe90()` is the `FUN_006485b0` receiver (`ECX/this`), not its stack
  manager argument.

## RETAIL TIME LAYERS

The proof keeps three distinct quantities separate.

### 1. Worker poll

`FUN_00662880` uses `SleepEx(10, TRUE)` inside its repeating worker loop.
This is a **10 ms poll sleep**, not physics cadence and not a simulation step.

### 2. Per-manager dispatch gate

`FUN_00710a70` configures cPhysicsManager through:

```text
FUN_00647860(manager, 0, 30.0)
```

`FUN_00647860` stores:

```text
period_ms = ROUND(1000.0 / 30.0) = 33
```

at manager offset `+0xe8`. `FUN_00647ef0` consumes this period field and
retains sub-period carry. Therefore the retail BManager gate has a nominal
30 Hz configuration with a quantized 33 ms millisecond gate.

### 3. Physics simulation quantum

`FUN_00712450` updates scheduler accumulator `+0x348` by:

```text
scale * 0.03333333507180214
```

Normal scheduler scale is `1.0`, so one admitted normal outer update contributes
approximately `1/30 s` to the accumulator.

`FUN_0070f170` proves the cPhysicsManager rate-field domain:

```text
+0x388 = rate
+0x38c = 1 / rate
+0x390 = rate / 30
+0x394 = 30 / rate
```

`FUN_00713050` then computes the number of fixed substeps from
`rate * accumulator`, executes substeps at `1/rate`, and subtracts
`substep_count/rate` from the accumulator.

The final numeric runtime value of `rate` is intentionally not guessed or frozen
by this contract. The fixed-step relationship itself is proven.

## CONSUMER

The direct consumer is the explicit runtime scheduler-authority seam introduced
by Phase 716. It must select `RuntimeSchedulerAuthority::RetailEvidence` from
this positive handoff and must not inherit host-development `1/60` pacing.

The runtime implementation must preserve the distinction between:

```text
10 ms worker poll
33 ms quantized manager dispatch gate
~1/30 s normal simulation accumulator contribution
1/rate inner physics substep
```

## GATES CHANGED

```text
retail_cadence_admitted = true
scheduler_authority = RetailEvidence
cPhysicsManager default +0x18 dispatch = proven
+0x388 rate domain / reciprocal = proven
inner fixed-step 1/rate semantics = proven
```

## LIMITS

- The proof admits only default BManager mode (`+0x529 == 0`). The alternate
  `+0x1c` path is not admitted.
- It does not claim one rendered frame equals one retail physics update.
- It does not promote worker 10 ms sleep to physics cadence.
- It does not promote host `1/60` pacing.
- It does not guess the final numeric runtime physics `rate`.
- It does not require original-game execution or runtime capture.

## REPRODUCTION

```bash
python3 tools/ghidra/build_s5_retail_outer_update_cadence.py \
  /path/to/SHIFT.exe.c \
  /path/to/SHIFT.exe \
  evidence/physics_manager_scheduler_entry_owner.json \
  --json-out evidence/s5_retail_outer_update_cadence.json
```

The builder rejects source hash drift, PE hash drift, function-fragment drift,
owner-slot drift, exact byte-window drift, or retail constant drift.

## NEXT STEP

Consume `SHIFT.RetailOuterUpdateCadence/1` in the native runtime through a strict
retail scheduler policy. The existing host-development pacer must remain a
separate non-retail path.
