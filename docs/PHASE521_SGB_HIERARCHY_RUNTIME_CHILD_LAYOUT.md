# Phase 521 — SGB HIERARCHY runtime child layout

Phase 521 records the exact serialized-to-runtime copy layout for SGB HIERARCHY child records.

## Source-backed transformation

`FUN_0069a6c0` reads each serialized child as 9 dwords (`0x24` bytes) and copies them into a runtime element with `0x28`-byte stride.

| Runtime offset | Source word |
|---:|---:|
| `+0x00` | word 6 |
| `+0x04` | word 3 |
| `+0x08` | word 4 |
| `+0x0c` | word 5 |
| `+0x10` | word 0 |
| `+0x14` | word 1 |
| `+0x18` | word 2 |
| `+0x1c` | word 7 |
| `+0x20` | word 8 |

The runtime array is allocated with a count prefix and `0x28`-byte elements. The existing serializer-side raw 9-dword child record remains intact in the IR.

## IR

`src/scene/sgb_object_runtime.py` now exposes:

- `runtime_element_bytes`;
- `runtime_destination_word_offsets`;
- `runtime_source_word_offsets`;
- the existing `runtime_copy_order`.

No semantic field names are assigned to these positions.

## Verification

`tests/test_sgb_object_runtime.py` verifies the complete source-word → runtime-offset mapping and element size.

## Boundary

This phase proves the binary copy topology performed by the retail runtime. It does not resolve the gameplay or rendering semantics of the nine child values.