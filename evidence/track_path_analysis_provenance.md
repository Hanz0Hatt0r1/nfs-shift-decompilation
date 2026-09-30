# Track/path analysis provenance

The live-memory track/path analyzer now embeds a canonical evidence schema in
every `track_path_analysis.json`. This prevents candidate counts produced under
different reverse-engineering assumptions from being compared as though they
were equivalent.

## Fingerprinted evidence

`analyze_track_paths.py` records:

- concrete class vtables used by candidate filters;
- every decoded layout field offset and primitive unpacking type;
- count-prefixed array contracts and element strides;
- identity policy for concrete-vtable profiles versus structural `AISpline`
  ownership;
- a SHA-256 fingerprint of that canonical manifest.

The manifest format is:

```text
SHIFT-TRACK-PATH-ANALYZER-EVIDENCE/1
```

The surrounding analysis format remains
`SHIFT-LIVE-MEMORY-TRACK-PATH-ANALYSIS/1`; provenance is an additive field.

## Audit

Use:

```bash
python3 tools/shift_live_dump/audit_track_path_analysis_provenance.py \
  /path/to/track_path_analysis.json
```

The audit status is:

| Status | Meaning |
|---|---|
| `current` | embedded fingerprint exactly matches the current evidence schema |
| `stale` | a fingerprint exists, but the current schema differs |
| `legacy-stale` | no fingerprint exists and at least one overlapping concrete vtable changed |
| `legacy-unversioned` | no fingerprint exists and no overlapping vtable mismatch proves staleness; layout parity still cannot be established |

Only `current` exits successfully.

## Supplied historical archive

The supplied `track_path_analysis.zip` contains generated result files but no
raw memory snapshots. Its `track_path_analysis.json` records:

```text
format = SHIFT-LIVE-MEMORY-TRACK-PATH-ANALYSIS/1
known_vtables.AISegmentPath = 0x00afca70

Path = 200
Incident.PathOwner = 200
AISegmentPath = 0
AIPolylinePath = 200
```

That archive predates analyzer evidence fingerprints. More importantly,
`0x00afca70` has since been source/PE-identified as the `AIMarker` table.
The retail `AISegmentPath` constructor and RTTI evidence identify
`0x00afc930`.

The archive is therefore `legacy-stale`. Its `AISegmentPath=0` result is not
evidence that the captured process contained no `AISegmentPath`; it only says
that the old scanner found no objects carrying the incorrectly assigned
`0x00afca70` table.

The same archive also predates the concrete `AIPathInfo` and `AIArea`
identity gates, so its 200-hit `Path` and `Incident.PathOwner` caps cannot be
compared directly with counts from the current analyzer.

Because the archive does not include the source snapshots, these counts cannot
be regenerated under the corrected evidence schema. A raw capture is required
for that comparison.

## Purpose

The provenance fingerprint does not claim that reverse engineering is
finished. It establishes which exact interpretation was used for a result, so
future corrections to vtables, layouts or array contracts make older outputs
machine-detectably stale instead of silently changing their meaning.
