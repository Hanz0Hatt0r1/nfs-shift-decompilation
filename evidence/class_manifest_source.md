# SHIFT joined class manifest evidence

This note records the joined class-level view produced from the retail RTTI
registry and reflection metadata extractors.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Manifest

`tools/shift_live_dump/build_shift_class_manifest.py` combines the output of
`extract_shift_rtti_registry.py` and
`extract_shift_reflection_fields.py` into one class-centric report.

Each class row contains:

- registration function, descriptor and resolved class name;
- parent descriptor, resolved parent name, full resolved ancestry and direct
  child names;
- reflection pointer/metadata symbols;
- all PE RTTI getters and vtable candidates plus `unique_vtable` when the
  evidence is unambiguous;
- reflection builder function names;
- every direct reflected field, preserving resolved names, type codes, offsets,
  flags and original source expressions.

The manifest does not flatten inherited fields into the derived class. Direct
reflection fields stay attached to the metadata block that defines them, while
`ancestry` records the inheritance chain separately.

## Retail corpus summary

On the supplied retail source/executable pair the joined view contains:

| Metric | Count |
|---|---:|
| registered classes | 315 |
| resolved class names | 315 |
| classes with direct reflected fields | 245 |
| direct reflection fields | 3122 |
| classes with a unique PE vtable candidate | 267 |

The joined counts reproduce the underlying RTTI and reflection extractor
results. No additional class identity, field offset or vtable is invented by
the manifest layer.

## Track/path slice

The manifest consolidates the evidence already used by the track/path
decompiler. Representative rows include:

| Class | Parent | Direct fields | Unique vtable |
|---|---|---:|---:|
| `AIArea` | `AIAreaBase` | 23 | `0x00afc048` |
| `AIPathInfo` | `BPersistent` | 8 | `0x00afb150` |
| `AIPolylinePath` | `AIPath` | 7 | `0x00afc678` |
| `Knot` | `BPersistent` | 6 | `0x00afbe28` |
| `AISpline` | `BPersistent` | 4 | none |
| `AISegmentPath` | `AIPath` | 10 | `0x00afc930` |
| `AIPolyPathNode` | `BPersistent` | 3 | `0x00afbfa8` |
| `AIPathNode` | `BPersistent` | 7 | `0x00afbf60` |

This makes the concrete-vtable classes and the intentionally structural
`AISpline` boundary visible in the same machine-readable artifact.

## Scope

The manifest is a discovery/indexing artifact. A unique vtable plus reflected
layout is strong class evidence, but ownership, update behavior, array
semantics and runtime meaning still require constructor/factory, call-site or
live-capture evidence before they are promoted into decompiler behavior.
