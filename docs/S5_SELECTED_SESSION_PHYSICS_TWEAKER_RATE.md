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

It waits for `SHIFT.exe` (or accepts `--pid`) and emits `SHIFT.SelectedSessionPhysicsTweakerRateSnapshot/1` only after all of these are simultaneously true for multiple stable samples:

- pinned PE header identity matches;
- the `PhysicsTweaker.xml` load call anchor matches the relocated retail image;
- the `DAT_00c130d2 -> FUN_0070f170` apply-call anchor matches;
- the source-backed `cPhysicsManager` vtable matches;
- manager `+0x2ab == 1` (set after `PhysicsTweaker.xml` returns);
- `DAT_00c130d2 > 0`;
- `cPhysicsManager +0x388 > 0`;
- `DAT_00c130d2 == cPhysicsManager +0x388`;
- `+0x38c/+0x390/+0x394` satisfy `1/rate`, `rate/30`, and `30/rate`.

A post-load observed `180` is valid runtime evidence. The tool does **not** admit `180` merely because it is the constructor default.

Example:

```powershell
shift_selected_session_rate_snapshot.exe `
  --process-name SHIFT.exe `
  --stable-samples 5 `
  --sample-interval-ms 100 `
  --output selected_session_physics_tweaker_rate.json
```

`--self-test` is CI-only. Its JSON explicitly has `ready=false`, `admission_eligible=false`, and cannot be promoted.

## Exact-binary adjudication

A real positive snapshot is promoted with:

```bash
python tools/build_selected_session_physics_tweaker_rate.py \
  selected_session_physics_tweaker_rate.json \
  /path/to/SHIFT.exe \
  --cadence evidence/s5_retail_outer_update_cadence.json \
  --json-out out/selected_session_physics_tweaker_rate_admission.json
```

The adjudicator recomputes the exact retail executable size, MD5, and SHA-256 and joins the snapshot to `SHIFT.RetailOuterUpdateCadence/1`. It rejects self-tests, identity drift, manager/global divergence, malformed rate relationships, or any attempt to use the constructor default as static admission evidence.

A positive result is `SHIFT.SelectedSessionPhysicsTweakerRate/1`.

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

Run the sampler against the pinned retail `SHIFT.exe` through the selected Silverstone/BMW session, adjudicate the resulting snapshot, then feed only the admitted numeric rate into `RetailOuterSchedulerContract::admit_loaded_inner_rate`. Do not map rendered frames directly to outer updates and do not substitute host `1/60` or constructor-default `180`.
