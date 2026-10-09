# Process 1D — slot3 caller/index compatibility boundary

## Why this matters

P1.3D still needs writer provenance for selected `HDVehicle+0x28b8` (slot3). Existing PC-retail machine proof already establishes the direct consumer call:

```text
FUN_00758b50
  -> 0x00758d6b call FUN_00755950
```

with callee receiver expression:

```text
HDVehicle+0x400+slot*0xa80
```

The project Drive database is `SHIFT.GhidraSQLiteIndex/1`. A naive SQL query against its legacy `callee` column returned zero callers for `FUN_00755950`, apparently contradicting the machine proof.

## Root cause

The source `callgraph.jsonl` and the SQLite row both contain the exact call in `raw_json`:

```json
{
  "from_function": "0x00758b50",
  "from_name": "FUN_00758b50",
  "instruction": "0x00758d6b",
  "to": "0x00755950",
  "to_name": "FUN_00755950",
  "indirect": false
}
```

But the v1 SQLite row has an empty legacy `callee` column. Therefore:

```text
legacy v1 callee-column matches = 0
raw_json-normalized matches      = 1
```

This is a **v1 column-population/query compatibility defect**, not a missing Ghidra call edge and not semantic evidence of carrier absence.

## Repair

`tools/ghidra/query_shift_sqlite.py` now accepts both index formats:

- `SHIFT.GhidraSQLiteIndex/2`: uses the dedicated caller/callee name/address columns;
- `SHIFT.GhidraSQLiteIndex/1`: normalizes call records from `raw_json` and supports caller/callee/callsite queries by either symbolic name or exact address.

The preferred format for new builds remains v2.

## Slot3 result

With v1 normalization applied:

- direct caller recovered: `FUN_00758b50`;
- callsite recovered: `0x00758d6b`;
- callee recovered: `FUN_00755950` / `0x00755950`;
- machine proof and normalized SQLite agree;
- heuristic vtable inventory: **2,533** tables / **22,416** slots, target hits: **0**;
- exported static-table inventory: **55,066** records / **956,464** raw exported bytes, literal target-pointer hits: **0**.

The vtable/static-table misses remain navigation-only negatives. They do not override direct retail machine evidence and do not rule out other indirect carriers.

## Consequence for slot3 provenance

The correct starting point is now unambiguous: use the proven `FUN_00758b50` four-wheel lifecycle and exact receiver `HDVehicle+0x400+slot*0xa80`. Combined with the `FUN_00755950` internal `+0x538` read, slot3 is selected `HDVehicle+0x28b8`.

The next P1.3D task is to trace exact qword/f64 alias/callee/bulk-copy writes that can reach that selected root. Numeric `0x28b8` collisions on unrelated objects remain inadmissible.

## Fail-closed gate

```text
direct call carrier proven by machine                = true
normalized v1 SQLite recovers machine call            = true
legacy v1 callee-column population gap proven         = true
vtable/static-pointer misses prove carrier absence    = false
slot3 writer provenance proven                        = false
P1.3 control producer complete                        = false
provider count                                        = 7
```
