# shift-live-dump

Non-stopping Linux memory snapshots for Need for Speed: SHIFT running under Wine or native Linux.

The primary path is Linux `process_vm_readv(2)`. The tool does not ptrace-attach the target and does not intentionally stop it. In `auto` mode it also opens `/proc/PID/mem` as a fallback when the kernel permits it.

## Build

```bash
make -C tools/shift_live_dump
```

## Commands

Inspect mappings:

```bash
./tools/shift_live_dump/shift-live-dump maps <PID>
```

Capture writable memory:

```bash
./tools/shift_live_dump/shift-live-dump snapshot <PID> captures/shift-0001
```

Capture other regions with `--regions all|heap|anonymous|writable|modules`.

Use repeated snapshots while the scene is running:

```bash
./tools/shift_live_dump/shift-live-dump watch <PID> captures/garage \
  --interval-ms 250 --count 20 --regions writable
```

Compare snapshots without loading whole regions into RAM:

```bash
./tools/shift_live_dump/shift-live-dump diff \
  captures/garage/snapshot-000000 \
  captures/garage/snapshot-000019 \
  captures/garage-diff
```

Default block size is 4 KiB.

## Streaming analysis

For a larger capture set, use the Python analyzer:

```bash
python3 tools/shift_live_dump/analyze.py \
  captures/garage \
  --out captures/garage/analysis
```

It compares only regions with the same start address and size in every snapshot and processes one block at a time. A 13 GiB capture therefore does not need 13 GiB of RAM.

Outputs:

- `analysis.json` — snapshot/common-region statistics and totals by memory category.
- `region_summary.csv` — changed-block and transition statistics per region.
- `block_candidates.csv` — repeatedly changing block addresses ranked by activity.

The analyzer is deliberately conservative: changing memory is a candidate signal, not proof that the block contains physics state.

For controlled reverse engineering, capture separate series around one action at a time (steering, throttle/brake, gear, camera) and compare those series.

## Field-level analysis

After the block-level pass, decode only fields that overlap bytes which actually
changed between snapshots:

```bash
python3 tools/shift_live_dump/analyze_fields.py \
  captures/garage \
  --out captures/garage/field_analysis
```

The default `auto` scope favors private writable/anonymous mappings and
excludes common GPU/Wine noise such as NVIDIA device mappings and temporary
Wine mappings. To inspect anonymous/heap memory only:

```bash
python3 tools/shift_live_dump/analyze_fields.py \
  captures/garage \
  --scope anonymous \
  --out captures/garage/field_analysis
```

Use `--scope all --include-noise` only when you explicitly need module/device
mappings.

Outputs:

- `field_analysis.json` — run metadata, skipped mappings and field-type counts.
- `field_candidates.csv` — changing aligned 16/32/64-bit integer and float candidates with all observed values.
- `structure_candidates.csv` — nearby high-signal fields grouped into structure candidates.
- `region_scope.csv` — regions actually considered and their changed-block ratios.

The field analyzer does not claim that a numeric interpretation is semantically
correct. Pointer hits only mean that an integer value falls inside a mapped
virtual-address range. Use controlled captures (one input/action at a time) to
turn these candidates into physics/state hypotheses.


## Event-aware transition analysis

After collecting a sequence of snapshots, rank abrupt changes by capture-order
transition:

```bash
python3 tools/shift_live_dump/analyze_events.py \
  captures/track \
  --out captures/track/event_analysis
```

The analyzer reads common regions in small blocks and records:

- `transition_summary.csv` — changed blocks, changed bytes and affected regions
  for every snapshot pair.
- `event_blocks.csv` — blocks ranked by the size and concentration of their
  largest transition.
- `event_clusters.csv` — nearby retained candidates that peak on the same
  transition.
- `event_analysis.json` — machine-readable metadata, transition totals, and the highest-scoring retained event summary (`peak_transition`, `peak_event_score`, `peak_address`, `peak_changed_bytes`).

`peak_transition=0` means `snapshot-000000 -> snapshot-000001`; the index is
only a capture-order coordinate. The analyzer intentionally does not label a
transition as a crash, physics update, camera action or input event. Such a
label requires a controlled capture whose action timing is known.

By default, `--scope auto` favors anonymous/heap memory and private writable mappings and excludes known GPU/Wine noise. Use `--scope anonymous` for anonymous+heap only, or `--scope all --include-noise` when you explicitly need device/module mappings.\n\nThe event score is:

`peak_changed_bytes * (1 + 1 / changed_transitions)`

so a large one-transition burst receives more emphasis than a similarly large
change spread across many transitions. This is a ranking heuristic, not a
physical measurement.
## Output

Each snapshot contains `manifest.json`, `maps.txt` and `regions/*.bin`. Region files are exactly the mapped size; bytes that could not be read are zero-filled and accounted for as `bytes_failed` in the manifest.

The manifest records PID, selector, page size, backend, mapping boundaries, permissions, path and read statistics.

The generated range list from the track/path analyzer can be fed directly to
the extractor without copying individual addresses:

```bash
python3 tools/shift_live_dump/extract_ranges.py \
  <full-capture> \
  track-path-targets \
  --preset none \
  --range-file track-targeted/track_path_analysis/next_capture_ranges.txt
```

`--range-file` accepts one `START:SIZE` range per line and ignores blank
lines and `#` comments. Multiple range files and explicit `--range`
arguments can be combined; ranges are merged before extraction.

## Evidence limits

A live snapshot is not an atomic process-wide state. SHIFT can mutate memory while the tool is reading it. Use the snapshots to locate stable structures, pointers, tables, state transitions and memory correlations; do not treat a multi-structure snapshot as proof that all values existed simultaneously.

Kernel ptrace-related access restrictions still apply. Start with SHIFT and the dumper under the same user. The tool does not weaken those protections.

## Track/path structure analysis

The track-path analyzer combines the current SHIFT.exe.c reverse-engineering evidence with live-memory snapshots:

```bash
python3 tools/shift_live_dump/analyze_track_paths.py \
  captures/track-targeted \
  --out captures/track-targeted/track_path_analysis
```

It scans 4-byte-aligned object candidates for these recovered layouts:

- `Path`: tangent at `+0x10/+0x14`, outside `+0x18`, centreDist `+0x1c`, StartNode `+0x20`, and path flags `+0x24..+0x27`.
- `Incident.PathOwner`: Path pointer at `+0xd8`, centre position at `+0xdc..+0xe4`, radius at `+0xe8`, and activity flags at `+0xf0..+0xf8`.
- `AISegmentPath`: num nodes `+0x10`, segment-node array `+0x18`, length `+0x1c`, cyclic/narrow flags `+0x20/+0x24`, spacing `+0x28`, path distance `+0x2c`, current node `+0x30`, EdgeStep `+0x34`.
- `AIPolylinePath`: num nodes `+0x10`, node array `+0x14`, length `+0x18`, width `+0x1c`, cyclic `+0x20`, spacing `+0x24`, default width `+0x28`.

Candidates are filtered against mapped SHIFT.exe vftable addresses and writable target pointers. The analyzer also follows stable 32-bit pointers leaving the selected ranges, clusters nearby heap targets, and writes capture windows for the original full snapshot.

Outputs:

- `track_path_analysis.json` — structure-hit counts, pointer clusters, and next capture windows.
- `{profile}.csv` — structural candidates for each recovered profile.
- `stable_external_pointers.csv` — stable writable pointers found outside the selected ranges.
- `pointer_target_clusters.csv` — dense target families and dominant source strides.
- `next_capture_windows.csv` / `next_capture_ranges.txt` — merged windows for the next extraction pass.

A zero hit count in a reduced capture means only that the selected ranges do not contain a matching object; it is not evidence that the structure is absent from the running game.
