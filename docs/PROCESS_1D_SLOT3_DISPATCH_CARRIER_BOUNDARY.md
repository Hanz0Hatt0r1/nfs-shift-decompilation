# Process 1D — slot3 `FUN_00755950` carrier/index boundary

## Why this matters

P1.3D still needs writer provenance for selected `HDVehicle+0x28b8` (slot3). The current Drive SQLite index reports no direct caller for `FUN_00755950`, but existing PC-retail machine proof already establishes a concrete direct call:

```text
FUN_00758b50
  -> 0x00758d6b call FUN_00755950
```

with callee receiver expression:

```text
HDVehicle+0x400+slot*0xa80
```

Therefore the SQLite miss is an **index coverage gap**, not evidence that the direct carrier is absent.

## Authority order

Direct retail machine evidence remains semantic authority. The navigation inputs are:

- `shift_ghidra.sqlite` — SHA-256 `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`;
- `vtables.json` — SHA-256 `15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed`;
- `static_tables.jsonl` — SHA-256 `798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2`;
- machine contract `SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1`.

The machine contract overrides contradictory index misses.

## Result

For target `FUN_00755950` (`0x00755950`):

- PC-retail machine proof: direct caller `FUN_00758b50`, callsite `0x00758d6b`;
- SQLite direct caller rows: **0**;
- SQLite covers the known machine call: **false**;
- heuristic vtable inventory: **2,533** tables / **22,416** slots, target hits: **0**;
- exported static-table inventory: **55,066** records / **956,464** raw exported bytes, literal little-endian pointer `0x00755950` hits: **0**.

The important conclusion is not that carriers are absent. It is:

```text
direct carrier proven by machine evidence        = true
SQLite caller index complete for this target     = false
vtable/static-table index misses prove absence   = false
```

This also means `query_shift_sqlite.py callers FUN_00755950` cannot be used as an authoritative negative result until the callgraph exporter/index path is repaired or regenerated.

## Consequence for slot3 provenance

The proven caller already supplies the useful lifecycle identity we need: `FUN_00758b50` passes wheel receivers from `HDVehicle+0x400+slot*0xa80` into `FUN_00755950`. Combined with the consumer's internal `+0x538` load, slot3 normalizes to selected `HDVehicle+0x28b8`.

So the next slot3 step does **not** require inventing a runtime indirect carrier. It should start from the proven `FUN_00758b50` wheel loop and trace exact alias/callee/bulk-copy writes that can reach the rear slot selected root. Candidate promotion still requires exact root provenance and qword/f64 width.

## Fail-closed gate

```text
direct call carrier proven by machine       = true
SQLite direct-callgraph complete             = false
index misses prove carrier absence            = false
runtime/other indirect dispatch ruled out     = false
slot3 writer provenance proven                = false
P1.3 control producer complete                = false
provider count                                = 7
```

Do not infer object identity from numeric offset equality. PC-retail machine evidence remains authoritative when an index disagrees.
