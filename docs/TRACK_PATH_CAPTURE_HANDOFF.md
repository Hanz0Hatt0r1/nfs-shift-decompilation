# Track/path capture handoff audit

The track-path analysis now has an explicit capture-completeness layer:

```bash
python3 tools/shift_live_dump/audit_track_path_capture.py \
  captures/track_path_analysis
```

The audit inventories the expected outputs of the track/path pipeline and
separates three states:

- `capture-structure-incomplete`: the static Path/AIW layer is incomplete.
- `runtime-correlation-blocked`: the static layer exists, but concrete
  runtime nodes, runtime edges or object joins are missing.
- `ready`: the instance-graph evidence is present and the next validation
  stages can run.

The report is written to `track_path_capture_handoff.json`.

## Root handoff

The audit reads `path_root_targets.csv` and `path_root_ranges.txt` and
retains high-value runtime roots without selecting a semantic interpretation.
For each root it preserves the original target, candidate count and mapping
context.

The report also emits reproducible commands for:

1. extracting the generated root ranges from the original full capture;
2. rerunning the track/path analyzer with the recovered runtime roots and AIW;
3. validating explicit AIW runtime edges;
4. validating the full AIW -> runtime node -> AIPolylinePath -> Path instance graph.

Use `--strict` in automation when a capture is required to contain a complete
runtime instance graph.

## Evidence boundary

The audit never upgrades an incomplete capture to a positive runtime result.
An empty runtime-match CSV, missing node array, or missing Path/Polyline join
remains an explicit blocker. The recommended command set is a handoff for the
next capture/re-analysis pass, not a semantic claim about the track-path
consumer.
