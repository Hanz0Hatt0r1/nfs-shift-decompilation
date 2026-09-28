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
- `event_analysis.json` — machine-readable metadata and transition totals.

`peak_transition=0` means `snapshot-000000 -> snapshot-000001`; the index is
only a capture-order coordinate. The analyzer intentionally does not label a
transition as a crash, physics update, camera action or input event. Such a
label requires a controlled capture whose action timing is known.

The event score is:

`peak_changed_bytes * (1 + 1 / changed_transitions)`

so a large one-transition burst receives more emphasis than a similarly large
change spread across many transitions. This is a ranking heuristic, not a
physical measurement.
\n## Output

Each snapshot contains `manifest.json`, `maps.txt` and `regions/*.bin`. Region files are exactly the mapped size; bytes that could not be read are zero-filled and accounted for as `bytes_failed` in the manifest.

The manifest records PID, selector, page size, backend, mapping boundaries, permissions, path and read statistics.

## Evidence limits

A live snapshot is not an atomic process-wide state. SHIFT can mutate memory while the tool is reading it. Use the snapshots to locate stable structures, pointers, tables, state transitions and memory correlations; do not treat a multi-structure snapshot as proof that all values existed simultaneously.

Kernel ptrace-related access restrictions still apply. Start with SHIFT and the dumper under the same user. The tool does not weaken those protections.
