# Process 1B — live exact render-manager root alias capture

## Blocker

`SHIFT.P1B.Manager374RuntimeRootFrontier/2` reduces the runtime root-origin frontier to three external classes. The narrowest surviving class is memory whose producer is not in the canonical program-internal lineage but which nevertheless contains the exact live outer-root pointer stored at `DAT_00bc185c`.

Static replay already proves that 112 direct machine loads from `DAT_00bc185c` produce zero bounded memory-store sinks. That does not exclude aliases initialized externally, by opaque helpers, or by unrecognized runtime dataflow. Because the root itself is a runtime pointer, this class needs live value evidence rather than another immediate-address scan.

## Tool

`tools/shift_live_dump/analyze_manager374_root_aliases.py` consumes existing `SHIFT-LIVE-MEMORY-SNAPSHOT/1` captures.

For each snapshot it:

1. requires the canonical root slot address `0x00bc185c` to be present in the capture;
2. reads the little-endian 32-bit root value from that snapshot;
3. skips snapshots where the root is null rather than scanning for zero;
4. streams every captured writable mapping and finds exact copies of that snapshot's root value;
5. excludes the canonical root slot itself from candidate output;
6. aggregates candidate addresses across snapshots, including cases where the runtime root value changes between object lifetimes.

The default scan uses byte alignment 1, so packed or otherwise unaligned pointer copies are not silently omitted. `--alignment 4` is available only as an explicit faster/narrower diagnostic mode.

## Reproduction

Capture several controlled lifecycle states while the render-manager root is active:

```bash
./tools/shift_live_dump/shift-live-dump watch <PID> captures/manager-root \
  --interval-ms 250 --count 20 --regions writable
```

Then scan exact aliases:

```bash
python3 tools/shift_live_dump/analyze_manager374_root_aliases.py \
  captures/manager-root \
  --out captures/manager-root/root-alias-analysis
```

Outputs:

- `analysis.json` — capture metadata, active root values, candidate counts and fail-closed adjudication;
- `exact_root_alias_candidates.csv` — every noncanonical address observed to contain the exact live root value, with mapping identity and snapshot coverage.

## Evidence semantics

A hit is a **candidate exact value alias**, not proof of semantic ownership. It must still be traced to its producer and consumer.

A zero result is likewise scoped only to the supplied snapshots and captured mappings. Live snapshots are not atomic process-wide states, and a finite capture sequence cannot prove that an external writer never creates an alias at another time.

Therefore this tool promotes only:

```text
live_exact_root_alias_capture_complete_for_supplied_snapshots=true
```

The following remain false regardless of a zero finite capture:

```text
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count remains **7**.

## Next step

Run multiple controlled captures covering construction, garage/menu lifetime, track load, active driving, teardown and return-to-menu. Classify every noncanonical exact-root hit by mapping, producer and consumer. Only after repeated lifecycle coverage plus producer closure should Process 1B consider narrowing the external/unknown-origin alias class.
