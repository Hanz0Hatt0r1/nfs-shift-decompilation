# SHIFT RTTI registry extraction evidence

This note records the first repository-wide pass over the retail RTTI
registration pattern that had previously been inspected one class at a time.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Extractor

`tools/shift_live_dump/extract_shift_rtti_registry.py` recognizes the recovered
registration sequence built around `FUN_00631740` /
`PTR_FUN_00aaa988`. For each registration it records:

- the registration function and class name;
- the descriptor base symbol/address;
- the parent descriptor symbol and resolved parent class where available;
- the reflection pointer slot and the corresponding metadata symbol;
- PE `mov eax,<descriptor>; ret` RTTI getters;
- aligned `.rdata` vtable candidates whose RTTI slot points at those getters;
- `unique_vtable` only when exactly one PE candidate survives.

If a class name is passed to `FUN_00631740` as `&DAT_...` rather than a C
literal, the extractor resolves that address through the supplied retail PE.
This covers names such as `Knot` without a manual alias table.

## Retail corpus summary

Running the extractor on the supplied retail pair produced:

| Metric | Count |
|---|---:|
| RTTI registrations | 315 |
| resolved class names | 315 |
| resolved parent class names | 312 |
| reflection metadata symbols | 273 |
| classes with descriptor-returning RTTI getters | 305 |
| classes with at least one matching vtable candidate | 275 |
| classes with exactly one matching vtable candidate | 267 |

A unique RTTI getter is not by itself sufficient to claim a unique class vtable.
Some shared/base RTTI getters are referenced by more than one vtable, and the
extractor preserves every candidate instead of selecting one heuristically.

## Track/path slice

| Class | Descriptor | Parent | Reflection metadata | RTTI getter | Vtable candidates |
|---|---:|---|---|---:|---:|
| `AIArea` | `0x00c0d588` | `AIAreaBase` | `DAT_00b8afac` | `0x006c3c30` | `0x00afc048` |
| `AIPathInfo` | `0x00c0d5a4` | `BPersistent` | `DAT_00b8afd4` | `0x006bc3e0` | `0x00afb150` |
| `AIPolylinePath` | `0x00c0d608` | `AIPath` | `DAT_00b8b11c` | `0x006cc3b0` | `0x00afc678` |
| `Knot` | `0x00c0d638` | `BPersistent` | `DAT_00b8b194` | `0x006c3000` | `0x00afbe28` |
| `AISpline` | `0x00c0d648` | `BPersistent` | `DAT_00b8b1bc` | none | none |
| `AISplineInfo` | `0x00c0d658` | `BPersistent` | `DAT_00b8b1e4` | none | none |
| `AISegmentPath` | `0x00c0d668` | `AIPath` | `DAT_00b8b210` | `0x006ce680` | `0x00afc930` |
| `AIPolyPathNode` | `0x00c0d678` | `BPersistent` | `DAT_00b8b238` | `0x006c3950` | `0x00afbfa8` |
| `AIPathNode` | `0x00c0d688` | `BPersistent` | `DAT_00b8b260` | `0x006c3940` | `0x00afbf60` |
| `AIPath` | `0x00c0d698` | `AIPathObj` | `DAT_00b8b288` | none | none |

This automatically reproduces the concrete identities already established by
the path evidence while also explaining the `AIPath` / `AISpline` boundary:
their registry descriptors and reflection metadata are real, but this PE getter
pattern does not supply a dedicated concrete vtable.

## Scope

The extractor is an evidence-discovery tool, not an automatic class renamer.
A single candidate is strong PE identity evidence, but constructor/factory and
field-use source anchors are still preferred before changing semantic analyzer
labels or runtime decoding behavior.
