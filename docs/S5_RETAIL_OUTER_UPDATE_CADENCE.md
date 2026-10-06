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
- positive `SHIFT.PhysicsManagerSchedulerEntryOwner/1` proving the source-backed
  cPhysicsManager vtable and slot `+0x18 -> FUN_00711b50`;
- exact retail PE byte windows covering registration, controller-list transport,
  BManager dispatch selection, scheduler argument forwarding, accumulator update,
  rate consumption, and the PhysicsTweaker default/load path.

No original-game execution or runtime capture is used.

## OUTPUT

`evidence/s5_retail_outer_update_cadence.json` publishes
`SHIFT.RetailOuterUpdateCadence/1` with the **outer scheduler cadence admitted**
for default BManager mode (`+0x529 == 0`). The contract deliberately does not
freeze the loaded session's inner physics rate until `PhysicsTweaker.xml` is
available or an equivalent source-backed loaded value is proved.

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

## DEFAULT DISPATCH MULTIPLICITY

`FUN_0070f940` contains a four-call debug/special path guarded by
`DAT_00c104a4`. The pinned PE places this byte in the zero-filled virtual tail of
`.data`, and the pinned decompile has no source-visible writer. Therefore the
ordinary initial/default path makes exactly one `FUN_007155e0` call.

The scheduler object starts with state `1`. Recovered state-transition surfaces
include `1 -> 2` and `2 -> 3` under the active-init condition. State `3` is the
steady active state in which `FUN_007155e9` forwards its float argument to
`FUN_00715380`. The contract therefore admits one steady scheduler invocation
per default manager dispatch; it does not claim that every boot state is already
state `3`.

## RETAIL TIME LAYERS

The proof keeps four quantities distinct.

### 1. Worker poll

`FUN_00662880` uses `SleepEx(10, TRUE)` inside its repeating worker loop. This is
a **10 ms poll sleep**, not physics cadence and not a simulation step.

### 2. Per-manager dispatch gate

The cPhysicsManager vtable at `0x00b04524` links initializer slot `+0x04` to
`FUN_00710a70` and scheduler slot `+0x18` to `FUN_00711b50`, binding cadence
configuration and dispatch to the same source-backed owner.

`FUN_00710a70` configures cPhysicsManager through:

```text
FUN_00647860(manager, 0, 30.0)
```

`FUN_00647860` stores:

```text
period_ms = ROUND(1000.0 / 30.0) = 33
```

at manager offset `+0xe8`. `FUN_00647ef0` consumes this period field and retains
sub-period carry. Thus the retail BManager gate has a nominal 30 Hz
configuration with a quantized 33 ms millisecond gate.

### 3. Normal scheduler accumulator contribution

`FUN_00712450` updates scheduler accumulator `+0x348` by:

```text
scale * 0.03333333507180214
```

Normal scheduler scale is `1.0`, so one admitted normal outer update contributes
approximately `1/30 s` to the accumulator.

### 4. Inner physics substep

`FUN_0070f170` proves the cPhysicsManager rate-field domain:

```text
+0x388 = rate
+0x38c = 1 / rate
+0x390 = rate / 30
+0x394 = 30 / rate
```

`FUN_00713050` computes the number of substeps from `rate * accumulator`, runs
those substeps at `1/rate`, and subtracts `substep_count/rate` from the
accumulator.

The PhysicsTweaker constructor `FUN_00748280` sets field `+0x492` to `0xb4`
(180). The property registrar names that exact offset `"tick rate"`. The loaded
PhysicsTweaker object is `DAT_00c12c40`, and:

```text
DAT_00c12c40 + 0x492 == DAT_00c130d2
```

`FUN_00710a70` loads `PhysicsTweaker.xml` into that object before passing
`DAT_00c130d2` to `FUN_0070f170`. Therefore **180 Hz is a proven constructor
default**, giving six `1/180 s` substeps for a normal `1/30 s` increment before
resource override, but it is not promoted to the final loaded session rate.

## CONSUMER

The direct consumer is the explicit runtime scheduler-authority seam introduced
by Phase 716. It may select `RuntimeSchedulerAuthority::RetailEvidence` for the
outer scheduler from this positive handoff and must not inherit host-development
`1/60` pacing.

The native consumer must preserve the distinction between:

```text
10 ms worker poll
33 ms quantized manager dispatch gate
~1/30 s normal scheduler accumulator contribution
1/rate inner physics substep
```

It must also keep the loaded inner rate fail-closed until the selected-session
PhysicsTweaker value is available. The constructor default `180` is not a license
to ignore a resource override.

## GATES CHANGED

```text
outer_scheduler_cadence_admitted = true
scheduler_authority = RetailEvidence (outer scheduler)
cPhysicsManager default +0x18 dispatch = proven
one steady scheduler invocation per default dispatch = proven
+0x388 rate domain / reciprocal = proven
inner fixed-step 1/rate semantics = proven
loaded session numeric rate = not frozen
```

## LIMITS

- Only default BManager mode (`+0x529 == 0`) is admitted; alternate `+0x1c` is not.
- The active scheduler state is admitted as a steady-state condition, not claimed
  for every boot instant.
- One rendered frame is not equated with one retail physics update.
- Worker 10 ms sleep is not physics cadence.
- Host `1/60` pacing is not retail cadence.
- Constructor-default 180 Hz is not promoted to the loaded session rate because
  `PhysicsTweaker.xml` may override it.
- No original-game execution or runtime capture is required.

## REPRODUCTION

```bash
python3 tools/ghidra/build_s5_retail_outer_update_cadence.py \
  /path/to/SHIFT.exe.c \
  /path/to/SHIFT.exe \
  evidence/physics_manager_scheduler_entry_owner.json \
  --json-out evidence/s5_retail_outer_update_cadence.json
```

The builder rejects source hash drift, PE hash drift, owner/vtable drift,
zero-fill/multiplicity drift, function-fragment drift, exact byte-window drift,
or retail constant drift.

## NEXT STEP

Consume the admitted **outer** scheduler authority in native runtime without
mapping one render-loop iteration directly to one inner physics step. Resolve the
selected-session PhysicsTweaker `tick rate`, then drive the existing persistent
BODY fixed-step boundary from the proven accumulator/substep rule.
