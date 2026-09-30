# Phase 545 — PART → FLAT runtime bridge

Phase 545 closes the source-backed bridge between the PART partition tree and
the FLAT runtime representation.

## Wrapper catalog used by PART

`FUN_006a4d10 -> FUN_0068a360` resolves each PART child-object id with:

```text
FUN_006885b0(loader_wrapper_list, source_id - 1)
```

The list order is source-backed:

1. OCCL records append a wrapper only in per-record mode;
2. NODE records append every wrapper;
3. SUMM bypasses this list and enters the FLAT manager directly through
   `FUN_00688510`.

`SHIFT.SGBPartFlatBridge/1` reconstructs that catalog and preserves both the
zero-based list index and the one-based PART source id.

Invalid id 0, an id beyond the catalog, duplicate partition ids, partition
cycles, unresolved child partitions and unreachable PART records fail closed.

## Finalization rule

`FUN_0068ab70` converts PART only when the scene graph has no FLAT manager at
`+0x30`.

Therefore the bridge has two explicit modes:

- `prebuilt-flat`: a FLAT chunk already populated the manager; no PART
  conversion is required;
- `part-to-flat`: PART is the available spatial source and the deterministic
  runtime conversion contract is emitted.

This keeps shipped/pre-normalized scenes separate from the fallback builder.

## Exact PART → FLAT accounting

`FUN_00689cb0` counts:

- `0x20` bytes for every PART node;
- `0x40` bytes for every direct scene wrapper in that node.

It also counts the total direct records used to allocate:

- primary runtime entries: `count * 0x28`;
- secondary runtime entries: `count * 0x40`.

The bridge emits and validates the same accounting.

## Direct-record build order

`FUN_00689db0` performs a deterministic depth-first build:

1. emit the current PART node;
2. emit all wrappers in the current node's container order;
3. recursively visit child partition slots 0 through 3.

For each direct record:

- FLAT record `+0x00..+0x0c` copies the four dwords at
  `(scene_wrapper +0x0c pointee) +0x10..+0x1c`;
- FLAT record `+0x38` stores that `scene_wrapper +0x0c` pointee;
- FLAT record `+0x3c` stores the sequential runtime index;
- primary entry `index*0x28 +0x20` points to the FLAT record;
- the secondary `index*0x40` entry is initialized from the wrapper by
  `FUN_00687b00` and receives:
  - parent FLAT node at `+0x30`;
  - FLAT direct record at `+0x34`;
  - primary entry at `+0x38`.

The PART AABB at runtime node `+0x04..+0x18` is copied into the FLAT node
header `+0x00..+0x14`.

## PART wrapper placement

Before conversion, `FUN_0068a360` also stores the PART bounds pointer in
scene wrapper `+0x30`. The bridge exposes this write as provenance on every
resolved direct record.

After the conversion, `FUN_00689d40 -> FUN_00687de0` tears down the PART
tree and clears the old wrapper payload linkage before the normalized FLAT
manager becomes the spatial runtime representation.

## Retail observation

The evidence file
`evidence/retail_sgb_spatial_representation_observation.json` records three
retail track samples without committing raw game data:

- Silverstone Era 3 Grand Prix;
- Hazyview Eight;
- Chesterglen.

All three use:

```text
OCCL → NODE → FLAT → SUMM → END
```

and contain no PART chunk. This matches the finalizer contract: these shipped
scenes already carry the prebuilt FLAT representation. PART→FLAT remains a
fully source-backed construction/fallback path rather than an invented format
relationship.

## IR integration

Every `SHIFT.SGBRuntime/1` report now contains `spatial_bridge`.

For a normal shipped track this reports `mode=prebuilt-flat`. For a
PART-only source it emits the generated node/direct-record/table geometry and
the exact wrapper-catalog joins.

## Boundary

Phase 545 proves spatial representation conversion and wrapper/index ownership.
It does not yet assign higher-level semantic names to the four dwords copied
from the wrapper `+0x0c` object into each FLAT direct record.

Those four values are now the next narrow scene target required to turn the
spatial bridge into renderer placement data.
