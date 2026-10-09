# Process 1D — slot3 `FUN_00755950` dispatch carrier boundary

## Why this matters

P1.3D still needs writer provenance for selected `HDVehicle+0x28b8` (slot3). The consumer is `FUN_00755950`, but the current Ghidra SQLite direct-call graph has no direct edge into that function. Before treating any local callgraph neighborhood as authoritative, this lane bounds the common static dispatch carriers that could explain how the consumer is reached.

## Authoritative navigation inputs

The analysis uses the current project Drive Ghidra bundle:

- `shift_ghidra.sqlite` — SHA-256 `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`;
- `vtables.json` — SHA-256 `15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed`;
- `static_tables.jsonl` — SHA-256 `798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2`.

These are navigation indexes. They narrow where to look; they are not substitutes for exact retail machine-flow proof.

## Result

For target `FUN_00755950` (`0x00755950`):

- direct callgraph callers: **0**;
- heuristic vtable inventory: **2,533** tables / **22,416** slots, target hits: **0**;
- exported static-table inventory: **55,066** records / **956,464** raw exported bytes, literal little-endian pointer `0x00755950` hits: **0**.

Therefore the currently exported static carrier classes are empty for this target:

```text
direct call edge                absent
heuristic vtable slot           absent
literal static function pointer absent
```

This does **not** prove that `FUN_00755950` is unreachable. Runtime registration, copied/relocated pointers, code-built function pointers, indirect calls, callback registries, virtual dispatch missed by the heuristic vtable exporter, and other dynamic carrier classes remain open.

## Consequence for slot3 provenance

The prior direct-store proof already established that `HDVehicle+0x28b8` has no direct literal store in the full PC-retail PE. This carrier result now also says that a writer search should not assume there is a direct caller or canonical static vtable entry around `FUN_00755950`.

The next productive path is to recover the runtime/code-built carrier that supplies `FUN_00755950` as an indirect target. That lifecycle should expose the exact selected `HDVehicle` root or owning object identity; only then should alias/callee/bulk-copy stores into `+0x28b8` be promoted.

## Fail-closed gate

```text
known exported static carriers empty      = true
runtime/code-built indirect dispatch ruled out = false
consumer unreachable proven               = false
slot3 writer provenance proven            = false
P1.3 control producer complete             = false
provider count                             = 7
```

Do not infer object identity from the numeric offset `0x28b8`, and do not promote a candidate unless selected-root provenance and write width are both exact.
