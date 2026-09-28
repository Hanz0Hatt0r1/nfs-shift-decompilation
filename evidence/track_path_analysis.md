# Track/path runtime structure analysis

## Capture

Input: `track-targeted.zip`

The reduced capture contains 10 snapshots and 5 common selected virtual-address ranges, for 7,700,480 bytes total.

The selected ranges are:

```text
0x03519000:0x23000
0x0cd67000:0x20000
0x18f72000:0x35000
0x21783000:0x24000
0x21922000:0x20000
```

## Structural scan

The analyzer was run with the recovered layouts for `Path`, `Incident.PathOwner`, `AISegmentPath`, and `AIPolylinePath`.

```text
Path=0
Incident.PathOwner=0
AISegmentPath=0
AIPolylinePath=0
```

This is an absence from the selected ranges only. The reduced capture does not contain the bytes addressed by the external pointers found below.

## Stable external pointer scan

2,303 distinct stable 32-bit pointers from the selected ranges point into writable mappings outside the selected ranges.

The strongest target families are:

| Rank | Target range | Distinct targets | Dominant source stride |
|---|---|---:|---:|
| 1 | `0x0b0a8560-0x0b0c80e1` | 238 | `0x60` over 236 transitions |
| 2 | `0x0b0dbf10-0x0b0e8211` | 91 | `0x60` over 89 transitions |
| 3 | `0x0b088700-0x0b08d7b1` | 47 | `0x60` over 46 transitions |
| 4 | `0x080d0700-0x080dfb01` | 54 | `0x94` over 26 transitions |
| 5 | `0x18fec218-0x18ff3a31` | 33 | `0x4` over 31 transitions |

The repeated `0x60` source stride is consistent with the 0x60-byte resource-record table visible in the selected `0x21922000` range. It establishes a strong allocator/table relationship but does not by itself identify the pointed-to objects as `Path` objects.

## Next extraction window

Using a 128 KiB radius around the strongest pointer clusters, the analyzer merges the first three families into:

```text
0x0b068700:0x9fb11
```

This is the first range to extract from the original full live-memory capture. The existing `tools/shift_live_dump/extract_ranges.py` accepts this `START:SIZE` syntax directly.

## Reverse-engineering anchors

The scanner encodes the following recovered structure anchors:

- `Path`: `tangent` +0x10/+0x14, `outside` +0x18, `centreDist` +0x1c, `StartNode` +0x20, flags +0x24..+0x27.
- `Incident.PathOwner`: `Path` +0xd8, centre position +0xdc..+0xe4, radius +0xe8, activity fields +0xf0..+0xf8.
- `AISegmentPath`: fields through +0x34; constructor vftable `0x00AFCA70`.
- `AIPolylinePath`: fields through +0x28.

These layouts are evidence-backed candidates from the current `SHIFT.exe.c` decompilation, not guesses derived solely from numeric memory patterns.

## Reproduction

```bash
python3 tools/shift_live_dump/analyze_track_paths.py \
  track-targeted \
  --out track-targeted/track_path_analysis

# Then extract the highest-priority range from the original full capture:
python3 tools/shift_live_dump/extract_ranges.py \
  <full-capture> \
  track-path-targets \
  --preset none \
  --range 0x0b068700:0x9fb11
```
