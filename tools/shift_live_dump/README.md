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

- `Path` (legacy output name for retail `AIPathInfo`): tangent at `+0x10/+0x14`, outside `+0x18`, centreDist `+0x1c`, StartNode `+0x20`, and path flags `+0x24..+0x27`; source constructor `FUN_006bc3a0` and PE RTTI getter `0x006bc3e0` identify concrete vtable `0x00afb150`. See [AIPathInfo evidence](../../evidence/ai_path_info_source.md).
- `Incident.PathOwner` (legacy profile name for the path-owner subset of retail `AIArea`): incident position `+0x30..+0x38`, area type `+0xd4`, Path pointer `+0xd8`, CentrePos `+0xdc..+0xe4`, Radius `+0xe8`, activity flags `+0xf0..+0xf8`, incident path distance `+0x100`, timer `+0x104`, interest `+0x108`, min spacing `+0x10c`, TrackDist `+0x110`, RaceFlag `+0x114`, AreaIndex `+0x118`, nMarshals `+0x11c`, and nFlagMarshals `+0x120`; source constructor `FUN_006c3a20` and PE RTTI getter `0x006c3c30` identify vtable `0x00afc048`. See [AIArea evidence](../../evidence/ai_area_source.md).
- `AISegmentPath`: reflection explicitly exposes num nodes `+0x10`, track side `+0x14`, segment-node array `+0x18`, length `+0x1c`, cyclic `+0x20`, NarrowPath `+0x24`, PathNodeSpacing `+0x28`, PathDist `+0x2c`, CurrentNode `+0x30`, and EdgeStep `+0x34`.
- `AIPathNode`: 0x38-byte `AISegmentPath` array element with reflected 2D positions, normal, heights, path distance and distribution ratio. See [segment node evidence](../../evidence/segment_path_node_source.md).
- `AIPolylinePath`: num nodes `+0x10`, node array `+0x14`, length `+0x18`, width `+0x1c`, cyclic `+0x20`, spacing `+0x24`, default width `+0x28`.
- `AIPolyPathNode`: 0x24-byte array element with 2D position/tangent fields at `+0x10..+0x1c` and cumulative path distance at `+0x20`.
- `Knot`: 0x48-byte `AISpline` element with `Pos`, `ConstantA/B/C`, `Length`, and `InvLength` fields. See [spline knot evidence](../../evidence/spline_knot_source.md).

The retail PE also defines how these fields are used for nearest-point and
path-distance queries. See [AIPolylinePath geometry evidence](../../evidence/polyline_path_geometry_source.md).

The same registration/RTTI machinery can be inspected repository-wide instead
of one class at a time:

```bash
python3 tools/shift_live_dump/extract_shift_rtti_registry.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --prefix AI \
  --json-out /tmp/shift-ai-rtti.json
```

The registry extractor recovers the registration function, class name,
descriptor, resolved parent class, reflection pointer slot/metadata symbol,
descriptor-returning PE RTTI getters, all matching vtable candidates, and a
`unique_vtable` only when the PE evidence is unambiguous. Names stored as
`DAT_...` string symbols are resolved from the executable, so classes such as
`Knot` do not need a hand-written name table. Multiple vtable candidates remain
multiple candidates rather than being collapsed to a guess. See
[RTTI registry evidence](../../evidence/rtti_registry_source.md).

Reflected field layouts can be extracted from the same retail pair:

```bash
python3 tools/shift_live_dump/extract_shift_reflection_fields.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --prefix AI \
  --json-out /tmp/shift-ai-fields.json \
  --csv-out /tmp/shift-ai-fields.csv
```

The field extractor joins every `FUN_0063a280` metadata call back to the RTTI
registry, recovers the owning class, field name, reflection type code, offset
and flags, and preserves the original expression when an offset or generated
name is dynamic. PE-backed string resolution also handles reflected names stored
as `DAT_...` or `PTR_s_...` symbols. See
[reflection field evidence](../../evidence/reflection_fields_source.md).

For class-centric work, join both sources into one manifest:

```bash
python3 tools/shift_live_dump/build_shift_class_manifest.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --prefix AI \
  --only-reflected \
  --json-out /tmp/shift-ai-classes.json \
  --csv-out /tmp/shift-ai-classes.csv
```

The class manifest keeps registration identity, descriptor, parent/ancestry,
direct children, reflection metadata/builders, direct reflected fields, RTTI
getters and vtable candidates together in one row per class. Inherited fields
are not flattened into derived classes; `ancestry` remains a separate evidence
chain. On the supplied retail pair it joins all 315 registered classes, 245
classes with direct reflected fields, 3122 direct fields, and 267 classes with
a unique PE vtable candidate. See
[class manifest evidence](../../evidence/class_manifest_source.md).

Track/path layout dictionaries can then be checked directly against those
recovered fields:

```bash
python3 tools/shift_live_dump/verify_track_path_reflection_layouts.py \
  /path/to/SHIFT.exe.c \
  --exe /path/to/SHIFT.exe \
  --analyzer tools/shift_live_dump/analyze_track_paths.py
```

The current verifier covers 62 reflected base offsets across `AIPathInfo`,
`AIArea`, `AISegmentPath`, `AIPathNode`, `AIPolylinePath`,
`AIPolyPathNode`, `Knot`, and `AISpline`. Vector-like reflected fields
are checked at their source base offset only; the verifier does not infer an
undocumented component count from the numeric reflection type code. See
[track/path reflection validation](../../evidence/track_path_reflection_layout_validation.md).

Before changing a concrete path vtable, validate the analyzer against the recovered
retail decompilation:

```bash
python3 tools/shift_live_dump/verify_track_path_source_anchors.py \
  /path/to/SHIFT.exe.c \
  --expect-source-sha256 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9 \
  --exe /path/to/SHIFT.exe \
  --expect-exe-sha256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

The verifier checks the source function/vtable anchors for `AIPathInfo`,
`AIArea`, `AISegmentPath`, `AIPathNode`, `AIPolylinePath`,
`AIPolyPathNode`, and `Knot`, verifies the factory RTTI-to-constructor links
for the two concrete path containers, and requires the recovered addresses to
match `KNOWN_VTABLES` in `analyze_track_paths.py`. With `--exe`, it uses
the shared generic PE RTTI index to recover the same vtables and asserts that
`AISpline`/`AISplineInfo` do not expose a dedicated getter through this
mechanism. A mismatch exits non-zero. See
[track/path RTTI vtable evidence](../../evidence/track_path_rtti_vtables.md).

Every newly generated `track_path_analysis.json` embeds a canonical evidence
manifest and SHA-256 fingerprint. Audit an older result before comparing counts:

```bash
python3 tools/shift_live_dump/audit_track_path_analysis_provenance.py \
  /path/to/track_path_analysis.json
```

The audit returns `current` only for an exact fingerprint match. Older outputs
without a fingerprint are `legacy-unversioned` unless an overlapping concrete
vtable already disagrees, in which case they are `legacy-stale`. Fingerprinted
outputs whose layouts/vtables/contracts changed are `stale`. See
[track/path analysis provenance evidence](../../evidence/track_path_analysis_provenance.md).

Candidates are filtered against mapped SHIFT.exe vtable addresses and writable target pointers. Legacy `Path`/`AIPathInfo`, `Incident.PathOwner`/`AIArea`, `AISegmentPath`, `AIPolylinePath`, and `AIPolyPathNode` require their recovered concrete vtables (`0x00afb150`, `0x00afc048`, `0x00afc930`, `0x00afc678`, and `0x00afbfa8`, respectively); generic executable vtables are not accepted as those concrete classes. The analyzer also follows stable 32-bit pointers leaving the selected ranges, clusters nearby heap targets, and writes capture windows for the original full snapshot.

Outputs:

- `track_path_analysis.json` — structure-hit counts, pointer clusters, next capture windows, and an `analyzer_evidence` manifest/fingerprint covering the vtables, layouts, array contracts and class-identity policies used to interpret the capture.
- `{profile}.csv` — structural candidates for each recovered profile. `aipolylinepath.csv` additionally records whether `array[-4]` matches `num nodes`, whether the first array element has the `AIPolyPathNode` vtable, and how many consecutive `0x24`-byte nodes were validated.
- `aipolylinepath_nodes.csv` — decoded elements of every fully validated `AIPolylinePath.array`, exported only when the count prefix and complete concrete-vtable sequence agree across every supplied snapshot; includes node address/index, 2D position/tangent and cumulative distance.
- `aisegmentpath_nodes.csv` — complete reference-snapshot `AISegmentPath.array` instances exported only when the count prefix and complete `AIPathNode` vtable sequence agree across every supplied snapshot, including reflected node fields.
- `aispline_knot_arrays.csv` / `aispline_knots.csv` — complete count-prefixed `Knot` arrays and their reflected fields from the reference snapshot.
- `aispline_knot_links.csv` — exact structural `AISpline` candidate pointer/count joins to validated `Knot` arrays across every supplied snapshot, with `owner_candidate_count` and `unique_owner`. The retail PE exposes no dedicated AISpline RTTI getter/vtable through the concrete-class pattern used by the neighboring path classes.
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
