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
