# Track/path runtime structure analysis

> **Historical provenance notice:** the runtime counts in this document were
> produced before analyzer evidence fingerprints and before the concrete
> `AIPathInfo`/`AIArea` gates and corrected `AISegmentPath` vtable were
> established. They remain useful as a record of capture progression, but must
> not be treated as current class-identification results without rerunning the
> present analyzer. See [track_path_analysis_provenance.md](track_path_analysis_provenance.md).


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

2,303 distinct stable 32-bit pointers are visible before source filtering. The selected `0x21922000-0x21942000` range is a resource table and generates most of the highest raw pointer clusters.

The strongest target families are:

| Raw rank | Target range | Distinct targets | Dominant source stride |
|---|---|---:|---:|
| 1 | `0x0b0a8560-0x0b0c80e1` | 238 | `0x60` over 236 transitions |
| 2 | `0x0b0dbf10-0x0b0e8211` | 91 | `0x60` over 89 transitions |
| 3 | `0x0b088700-0x0b08d7b1` | 47 | `0x60` over 46 transitions |
| 4 | `0x080d0700-0x080dfb01` | 54 | `0x94` over 26 transitions |
| 5 | `0x18fec218-0x18ff3a31` | 33 | `0x4` over 31 transitions |

The repeated `0x60` source stride is consistent with the 0x60-byte resource-record table visible in the selected `0x21922000` range. The first three raw clusters are directly sourced by records whose `+0x04/+0x08` fields resolve to Silverstone `twall_cover`, `trackedge`, and `terrain` `.meshtype` names, so they are render/resource-cache evidence rather than track-physics evidence. The common `0x0b9636a0` pointer is also a shared manager/sentinel reference and is treated as noise.

## Next extraction window

For track/physics work, the resource-table source range is excluded with:

```bash
python3 tools/shift_live_dump/analyze_track_paths.py \
  track-targeted \
  --out track-targeted/track_path_analysis_filtered \
  --exclude-source-range 0x21922000:0x20000
```

The filtered pass leaves 1,343 stable external pointers. Its highest non-resource target family is:

```text
0x080d0700-0x080dfb01
54 distinct targets
source stride 0x94 over 26 transitions
```

Using the existing 128 KiB target radius, the resulting first non-resource extraction window is:

```text
0x080b0700:0xc45c1
```

This is the first range to extract from the original full live-memory capture. The existing `tools/shift_live_dump/extract_ranges.py` accepts this `START:SIZE` syntax directly, and the generated `next_capture_ranges.txt` can also be supplied with `--range-file`.

## Reverse-engineering anchors

The scanner encodes the following recovered structure anchors:

- `Path` is the legacy analyzer label for retail `AIPathInfo`: `tangent` +0x10/+0x14, `outside` +0x18, `centreDist` +0x1c, `StartNode` +0x20, flags +0x24..+0x27; concrete vftable `0x00AFB150`.
- `Incident.PathOwner` is the legacy analyzer label for the path-owner subset of retail `AIArea`: `Path` +0xd8, centre position +0xdc..+0xe4, radius +0xe8, activity fields +0xf0..+0xf8; concrete vftable `0x00AFC048`.
- `AISegmentPath`: fields through +0x34; constructor vftable `0x00AFC930`.
- `AIPolylinePath`: fields through +0x28.

These layouts are evidence-backed candidates from the current `SHIFT.exe.c` decompilation, not guesses derived solely from numeric memory patterns.

## Reproduction

```bash
python3 tools/shift_live_dump/analyze_track_paths.py \
  track-targeted \
  --out track-targeted/track_path_analysis

# Exclude the resource-table source range:
python3 tools/shift_live_dump/analyze_track_paths.py \
  track-targeted \
  --out track-targeted/track_path_analysis_filtered \
  --exclude-source-range 0x21922000:0x20000

# Then extract the first non-resource window from the original full capture:
python3 tools/shift_live_dump/extract_ranges.py \
  <full-capture> \
  track-path-targets \
  --preset none \
  --range 0x080b0700:0xc45c1
```

## New `track-path-targets` follow-up capture

A second reduced capture targeted at the first non-resource window was supplied as `track-path-targets.zip`.
The capture contains 10 snapshots of the range `0x080b0700:0xc45c1`.

The current structural scan found:

```text
Path=4
Incident.PathOwner=25
AISegmentPath=0
AIPolylinePath=0
```

Three `Path` candidates form a particularly coherent family because they are
stable in all 10 snapshots, share the same header pattern, and expose mapped
`StartNode` targets:

| Path address | StartNode | Stable snapshots |
|---|---|---:|
| `0x08101010` | `0x33580000` | 10/10 |
| `0x081040d0` | `0x33630000` | 10/10 |
| `0x08107190` | `0x33630000` | 10/10 |

The fourth hit at `0x0812da7c` has `StartNode=0` and an unaligned header value
(`0x00aaffff`), so it is retained as a low-confidence structural candidate
rather than being used as a path root.

Each of the two non-null StartNode targets is referenced by 24 stable pointer
sources inside the captured range. The target mapping is the large writable
heap region `0x33412000-0x348e0000`.

The next capture should therefore follow the field-derived roots directly:

```text
0x33560000:0x40000   # 128 KiB radius around 0x33580000
0x33610000:0x40000   # 128 KiB radius around 0x33630000
```

This is a more direct follow-up than the generic pointer-cluster windows:
the roots come from the recovered `Path.StartNode` field itself.

Generated by the updated analyzer, these ranges will be emitted to
`path_root_ranges.txt` for direct use with `extract_ranges.py --range-file`.