# S5 — selected-session PhysicsTweaker rate admission

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`selected-session-physics-tweaker-rate-admission`: the strict retail outer scheduler is already admitted, but persistent BODY inner substeps must not use a guessed rate. The constructor default `180 Hz` is insufficient because `PhysicsTweaker.xml` is loaded before the rate is applied to `cPhysicsManager`.

## Static boundary

Pinned retail evidence establishes this order in `FUN_00710a70`:

```text
FUN_0074d400(&DAT_00c12c40)
  -> resolves and loads PhysicsTweaker.xml
...
FUN_0070fe90()->+0x2ab = 1
...
FUN_0070f170(cPhysicsManager, (uint16)DAT_00c130d2)
```

`FUN_0070f170` materializes the manager rate domain:

```text
cPhysicsManager +0x388 = rate
cPhysicsManager +0x38c = 1/rate
cPhysicsManager +0x390 = rate/30
cPhysicsManager +0x394 = 30/rate
```

`FUN_007117e0` may later adapt `+0x388`. Therefore the value loaded from `DAT_00c130d2` and the current manager rate are deliberately separate evidence domains.

The exact pinned retail executable remains:

```text
size    8,801,792
MD5     705af8b420e5eb1e3834ac43d5533c6b
SHA256  eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
PE timestamp 0x4af2ddcf
SizeOfImage 0x00995000
```

## Runtime snapshot producer

`native_capture/selected_session_rate_snapshot.cpp` builds as:

```text
shift_selected_session_rate_snapshot.exe
```

It waits for `SHIFT.exe` (or accepts `--pid`) and emits `SHIFT.SelectedSessionPhysicsTweakerRateSnapshot/1` after the loaded rate is stable for multiple samples and all loaded-rate identity prerequisites are positive:

- pinned PE header identity matches;
- the `PhysicsTweaker.xml` load call anchor matches the relocated retail image;
- the `DAT_00c130d2 -> FUN_0070f170` apply-call anchor matches;
- the source-backed `cPhysicsManager` vtable matches;
- manager `+0x2ab == 1` (set after `PhysicsTweaker.xml` returns);
- `DAT_00c130d2 > 0`.

The same samples also record current `cPhysicsManager +0x388/+0x38c/+0x390/+0x394` and report whether the manager currently equals the loaded value and whether the reciprocal relationships are coherent. Those observations do **not** gate proof of what `PhysicsTweaker.xml` loaded, because the manager rate may subsequently be adapted.

A post-load observed `180` is valid runtime evidence. The tool does **not** admit `180` merely because it is the constructor default.

Example:

```powershell
shift_selected_session_rate_snapshot.exe `
  --process-name SHIFT.exe `
  --stable-samples 5 `
  --sample-interval-ms 100 `
  --output selected_session_physics_tweaker_rate.json
```

`--self-test` is CI-only. It deliberately uses `loaded=240` and `current-manager=210` to prove that loaded-rate admission is independent from the later adaptive manager-rate policy. The raw self-test may report `ready=true`, but the exact-binary adjudicator always rejects `self_test=true`, so it can never become retail evidence.

## Exact-binary adjudication

A real positive snapshot is promoted with:

```bash
python tools/build_selected_session_physics_tweaker_rate.py \
  selected_session_physics_tweaker_rate.json \
  /path/to/SHIFT.exe \
  --cadence evidence/s5_retail_outer_update_cadence.json \
  --json-out out/selected_session_physics_tweaker_rate_admission.json
```

The adjudicator recomputes the exact retail executable size, MD5, and SHA-256 and joins the snapshot to `SHIFT.RetailOuterUpdateCadence/1`. It rejects self-tests, identity drift, an unstable/non-positive loaded value, missing post-load evidence, or any attempt to use the constructor default as static admission evidence.

A current manager/global mismatch does not erase the loaded-rate proof. Instead it produces the next blocker:

```text
current-manager-rate-scheduling-policy
```

If the manager equals the loaded value and its reciprocal domain is coherent at observation time, the next blocker becomes:

```text
inner-substep-runtime-consumption
```

A positive loaded-rate result is `SHIFT.SelectedSessionPhysicsTweakerRate/1`; it still does not admit inner execution by itself.

## Gates

Infrastructure now ready:

```text
selected_session_rate_snapshot_tool_ready = true
selected_session_rate_adjudicator_ready = true
```

Still closed until a real retail session is sampled and adjudicated:

```text
selected_session_rate_observation_present = false
loaded_inner_physics_rate_admitted = false
retail_inner_substep_execution_admitted = false
```

## NEXT_STEP

Run the sampler against the pinned retail `SHIFT.exe` through the selected Silverstone/BMW session and adjudicate the resulting snapshot. Then resolve whichever blocker the observation selects: adaptive current-manager rate scheduling if `+0x388` diverges, otherwise inner-substep runtime consumption. Do not map rendered frames directly to outer updates and do not substitute host `1/60`, the outer `33 ms` gate, or constructor-default `180`.
