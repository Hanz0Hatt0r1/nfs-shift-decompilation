# SHIFT.exe-anchored playable Linux bootstrap

## Blocker reduced

The playable Linux bootstrap previously required the operator to enumerate game
corpus archives manually (`Vehicles.zip`, `Silverstone_Era3_.zip`,
`SHIFT_tail.zip`, or equivalent BFF paths) and also provide a separate PE-image
evidence path. That is unnecessary when a complete retail installation already
exists.

`tools/run_playable_from_shift_exe.py` makes the installed `SHIFT.exe` the single
retail-install anchor.

The wrapper:

1. validates that the supplied file is named `SHIFT.exe`;
2. walks a bounded parent chain and finds the nearest unique `Pakfiles` directory;
3. verifies that the current Silverstone + BMW milestone archive names are present
   exactly once under that tree;
4. passes the discovered `Pakfiles` directory to the existing fail-closed playable
   bootstrap;
5. passes the same `SHIFT.exe` as `--renderer-pe-image`;
6. keeps all existing SHA-256 archive admission, renderer evidence, profile and
   runtime validation gates intact;
7. launches the generated continuous interactive profile unless
   `--bootstrap-only` is requested.

The basename preflight is discovery only. It does not replace
`SHIFT.RetailArchiveIdentityAdmission/1` or any downstream hash/provenance gate.

## Required retail files

The current first playable target still requires these archive identities inside
the discovered `Pakfiles` tree:

```text
Silverstone_Era3_GrandPrix.bff
Silverstone_Era3_GrandPrix_Physics.bff
BMW_M3_E36.bff
BMW_M3_E36_Cockpit.bff
RENDER.bff
```

The wrapper rejects a missing basename and also rejects multiple occurrences of a
required basename instead of choosing one by path order.

## Renderer capture boundary

The D3D9 capture is not part of the retail game installation, so it is not derived
from the `SHIFT.exe` location. Supply either:

```text
--renderer-capture-jsonl <capture.jsonl>
```

or:

```text
--renderer-capture-result <capture-result.json>
```

When neither is supplied, the wrapper looks for `shift_d3d9_capture.jsonl` in the
current working directory and then in the repository root.

## Live progress logging

The installed-game path intentionally still passes the complete discovered
`Pakfiles` tree to the existing bootstrap. Large retail installs can therefore
spend a long time inside catalog/resource analysis.

The launcher now activates `tools/resource_progress_site/sitecustomize.py` only
for the playable-bootstrap child. The instrumentation wraps the existing BFF
reader and orchestration calls; it does not replace a parser, alter archive
selection, or change an admission decision.

A normal catalog pass now reports real archive completion counts:

```text
[resource-progress] event=hooks-installed entry_interval=250
[resource-progress] phase=resource-catalog event=discovering-archives
[resource-progress] phase=resource-catalog event=start archives_total=412
[resource-progress] phase=resource-catalog archive=1/412 status=open done=0/412 percent=0.0 name=BOOTFLOW.bff
[resource-progress] phase=resource-catalog archive=1/412 status=header entries=843 name=BOOTFLOW.bff
[resource-progress] phase=resource-catalog archive=1/412 entry=250/843 entry_percent=29.7 name=BOOTFLOW.bff
[resource-progress] phase=resource-catalog archive=1/412 entry=500/843 entry_percent=59.3 name=BOOTFLOW.bff
[resource-progress] phase=resource-catalog archive=1/412 entry=843/843 entry_percent=100.0 name=BOOTFLOW.bff
[resource-progress] phase=resource-catalog archive=1/412 status=done done=1/412 processed=1/412 percent=0.2 name=BOOTFLOW.bff
```

`done=X/Y` is incremented only when that BFF context finishes successfully in the
current phase. Reopening the same archive later in the same resource-pipeline
phase does not inflate the count. A constructor/context failure is reported as
`status=failed` and contributes to `processed`, not `done`.

The resource entry counter is emitted for the first entry, every 250 entries, and
the final entry, so one large BFF cannot make the archive-level counter appear
frozen.

The later scene-IR pass starts a fresh archive counter:

```text
[resource-progress] phase=scene-ir event=start archives_total=412
...
[resource-progress] phase=scene-ir archive=412/412 status=done done=412/412 processed=412/412 percent=100.0 name=...
[resource-progress] phase=scene-ir event=complete processed=412/412 done=412 failed=0
```

The existing subprocess lifecycle heartbeat remains enabled as an independent
liveness signal:

```text
[shift-launch] stage=playable-bootstrap event=start ...
[shift-launch] stage=playable-bootstrap event=spawn pid=12345 heartbeat=10s
[shift-launch] stage=playable-bootstrap event=heartbeat pid=12345 elapsed=10.0s status=running
[shift-launch] stage=playable-bootstrap event=exit pid=12345 elapsed=... returncode=0
```

The bootstrap heartbeat is emitted every 10 seconds. After the native runtime is
launched, the same wrapper emits a lower-frequency 60-second heartbeat so a
long-running interactive session does not flood the terminal.

Neither the archive percentage nor the heartbeat is a semantic readiness
percentage. They expose execution progress only and do not weaken any fail-closed
evidence gate.

## Current command

From the repository root:

```bash
python3 tools/run_playable_from_shift_exe.py \
  "/path/to/Need for Speed SHIFT/SHIFT.exe" \
  --renderer-capture-jsonl shift_d3d9_capture.jsonl
```

For a bootstrap/profile validation pass without launching the native runtime:

```bash
python3 tools/run_playable_from_shift_exe.py \
  "/path/to/Need for Speed SHIFT/SHIFT.exe" \
  --renderer-capture-jsonl shift_d3d9_capture.jsonl \
  --bootstrap-only
```

The generated profile remains:

```text
out/playable-bootstrap/vertical_slice_profile.json
```

## Evidence boundary

This is orchestration infrastructure only. It does not claim that:

- install-layout proximity proves archive identity;
- the host interactive loop is the recovered retail scheduler;
- BODY0 bind-frame provenance is solved;
- retail input-to-drivetrain semantics are solved;
- vehicle-follow camera timing is solved.

It removes repeated manual game-file path selection while preserving the current
Process 1 -> Process 2 -> Process 3 evidence boundaries.
