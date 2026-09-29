# Phase 522 — SGB OBJECT/HIERARCHY/DAMAGE runtime wrappers

Phase 522 records the concrete runtime wrapper classes constructed by the SGB object dispatcher `FUN_0069a6c0`.

## Proven constructors

| Object kind | Constructor | Concrete vtable | Allocation |
|---|---|---:|---:|
| OBJECT | `FUN_00698dc0` / `FUN_00698dd0` initializer | `0x00af86b0` | `0xb0` bytes |
| HIERARCHY | `FUN_00698a20` | `0x00af8620` | `0xa0` bytes |
| DAMAGE | `FUN_00698b00` | `0x00af7c88` | `0xa0` bytes |

## Proven wrapper fields

For OBJECT, `FUN_0069a6c0` stores the parsed RESOURCE object at wrapper `+0x80` and MatrixNumber at `+0x84`.

For HIERARCHY, the runtime wrapper stores hierarchy type at `+0x80`, hierarchy count at `+0x84`, the runtime child-array pointer at `+0x88`, and MatrixNumber at `+0x94`. Child elements use the Phase 521 `0x28`-byte runtime layout.

For DAMAGE, only the concrete constructor/vtable and allocation size are recorded in this phase; deeper fields remain raw.

## IR

`src/scene/sgb_object_runtime.py` exposes `runtime_wrapper` with the constructor, initializer where proven, vtable, allocation size and proven field offsets.

## Boundary

This phase classifies the runtime wrapper object type created from the serialized payload kind. It does not assign gameplay or rendering semantics to the wrapper fields.