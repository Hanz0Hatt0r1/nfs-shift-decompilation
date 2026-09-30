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

The analyzer now resolves the AIPolylinePath array against the count-prefixed node allocation and exposes the verified node-array link in the CSV output.

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

### Following `Path.StartNode` directly

When the analyzer finds stable `Path` candidates with a non-null `StartNode`,
it emits:

- `path_root_targets.csv` — unique StartNode targets and the Path objects that reference them.
- `path_root_windows.csv` — merged extraction windows around those targets.
- `path_root_ranges.txt` — ready-to-use `START:SIZE` ranges.

The radius is controlled by `--path-root-radius-kib` (default 128 KiB), and
the number of followed roots by `--path-root-top`.

Use the generated roots directly against the original full capture:

```bash
python3 tools/shift_live_dump/extract_ranges.py \
  <full-capture> \
  track-path-roots \
  --preset none \
  --range-file track-targeted/track_path_analysis/path_root_ranges.txt
```

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
- `Incident.PathOwner`: incident position `+0x30..+0x38`, area type `+0xd4`, Path pointer `+0xd8`, CentrePos `+0xdc..+0xe4`, Radius `+0xe8`, activity flags `+0xf0..+0xf8`, incident path distance `+0x100`, timer `+0x104`, interest `+0x108`, min spacing `+0x10c`, TrackDist `+0x110`, RaceFlag `+0x114`, AreaIndex `+0x118`, nMarshals `+0x11c`, and nFlagMarshals `+0x120`.
- `AISegmentPath`: reflection explicitly exposes num nodes `+0x10`, track side `+0x14`, segment-node array `+0x18`, length `+0x1c`, cyclic `+0x20`, NarrowPath `+0x24`, PathNodeSpacing `+0x28`, PathDist `+0x2c`, CurrentNode `+0x30`, and EdgeStep `+0x34`.
- `AIPathNode`: 0x38-byte `AISegmentPath` array element with reflected 2D positions, normal, heights, path distance and distribution ratio. See [segment node evidence](../../evidence/segment_path_node_source.md).
- `AIPolylinePath`: num nodes `+0x10`, node array `+0x14`, length `+0x18`, width `+0x1c`, cyclic `+0x20`, spacing `+0x24`, default width `+0x28`.
- `AIPolyPathNode`: 0x24-byte array element with 2D position/tangent fields at `+0x10..+0x1c` and cumulative path distance at `+0x20`.
- `Knot`: 0x48-byte `AISpline` element with `Pos`, `ConstantA/B/C`, `Length`, and `InvLength` fields. See [spline knot evidence](../../evidence/spline_knot_source.md).

The retail PE also defines how these fields are used for nearest-point and
path-distance queries. See [AIPolylinePath geometry evidence](../../evidence/polyline_path_geometry_source.md).

Candidates are filtered against mapped SHIFT.exe vtable addresses and writable target pointers. `AISegmentPath`, `AIPolylinePath`, and `AIPolyPathNode` require their recovered concrete vtables (`0x00afca70`, `0x00afc678`, and `0x00afbfa8`, respectively); generic executable vtables are not accepted as those concrete classes. The analyzer also follows stable 32-bit pointers leaving the selected ranges, clusters nearby heap targets, and writes capture windows for the original full snapshot.

Outputs:

- `track_path_analysis.json` — structure-hit counts, pointer clusters, and next capture windows.
- `{profile}.csv` — structural candidates for each recovered profile. `aipolylinepath.csv` additionally records whether `array[-4]` matches `num nodes`, whether the first array element has the `AIPolyPathNode` vtable, and how many consecutive `0x24`-byte nodes were validated.
- `aipolylinepath_nodes.csv` — decoded elements of every fully validated `AIPolylinePath.array`, including node address/index, 2D position/tangent and cumulative distance.
- `aisegmentpath_nodes.csv` — complete reference-snapshot `AISegmentPath.array` instances with matching count prefix and concrete `AIPathNode` vtable, including reflected node fields.
- `aispline_knot_arrays.csv` / `aispline_knots.csv` — complete count-prefixed `Knot` arrays and their reflected fields from the reference snapshot.
- `aispline_knot_links.csv` — exact `AISpline` candidate pointer/count joins to validated `Knot` arrays across every supplied snapshot, with owner ambiguity counts. The object's concrete vtable remains unidentified.
- `aiw_next_edges.csv` — normalized `WP_PTRS.next` graph edges from the selected AIW resources, including waypoint indices and lap-distance delta.
- `aiw_runtime_edges.csv` — runtime-address pairs for each explicit AIW next edge, preserving the concrete in-memory graph and runtime stride/wrap information.
- `path_start_node_links.csv` — direct `Path.StartNode` resolutions, including target vtable, count-prefix stability and validated consecutive node count.
- `stable_external_pointers.csv` — stable writable pointers found outside the selected ranges.
- `pointer_target_clusters.csv` — dense target families and dominant source strides.
- `next_capture_windows.csv` / `next_capture_ranges.txt` — merged windows for the next extraction pass.
- `aiw_runtime_graph_validation.json` / `aiw_runtime_edge_groups.csv` — explicit AIW/runtime edge coverage, stride and ambiguity diagnostics from `validate_aiw_runtime_graph.py`.
- `path_polyline_links.csv` — exact `Path.StartNode == AIPolylinePath.array` joins with node-count/sequence consistency fields.
- `track_path_instance_graph.json` / `track_path_instance_edges.csv` — AIW runtime edges cross-checked against concrete `AIPolyPathNode` owners and exact Path/AIPolylinePath instances.
- `track_path_capture_handoff.json` — capture completeness audit, blocking evidence, recovered root candidates, and reproducible next extraction/correlation commands.

### Correlating runtime nodes with static AIW waypoints

The analyzer can now read the real track AIW directly from a `.aiw`, `.bff`,
a ZIP containing them, or a directory:

```bash
python3 tools/shift_live_dump/analyze_track_paths.py \
  capture/track-path-roots \
  --out capture/track-path-roots/track_path_analysis \
  --skip-pointer-analysis \
  --aiw /path/to/Silverstone_Era3_.zip \
  --aiw-entry 'grandprix' \
  --runtime-root 0x33580000 \
  --runtime-root 0x33630000
```

The AIW parser reads the `[Waypoint]` records, `wp_pos`, `wp_branchID`,
`wp_score` and `WP_PTRS`. Runtime correlation first uses exact
`AIPolyPathNode` candidates when present, matching their 2D coordinates against
the selected AIW plane (default `x/z`). For each selected AIW resource without
an exact node match, it falls back to the generic 3-float scan. It then looks
for long `WP_PTRS.next` address sequences with a constant stride.

Outputs:

- `aiw_waypoints.csv` — normalized static waypoint records from every selected AIW.
- `aiw_runtime_matches.csv` — individual runtime position matches with distance.
- `aiw_runtime_sequences.csv` — contiguous runtime waypoint sequences, inferred node stride, and `wp_pos` offset relative to the supplied runtime root.
- `track_path_analysis.json` — AIW source metadata, match count and inferred sequences.

Use `--aiw-range START:SIZE` when the exact heap window is already known.
`--runtime-root` is a convenience form that expands each root by
`--aiw-root-radius-kib` (default 128 KiB). To prevent accidental scans of
multi-gigabyte captures, unrestricted AIW correlation is refused above 64 MiB.

A zero hit count in a reduced capture means only that the selected ranges do not contain a matching object; it is not evidence that the structure is absent from the running game.

When a selected range is known to be an asset/resource table, pointer-source
noise can be excluded without changing the structural scan:

```bash
python3 tools/shift_live_dump/analyze_track_paths.py \
  captures/track-targeted \
  --out captures/track-targeted/track_path_analysis_filtered \
  --exclude-source-range 0x21922000:0x20000
```

The option is repeatable and applies only to the source addresses of stable
external pointers. It does not remove target objects merely because they fall
inside an excluded source range.
