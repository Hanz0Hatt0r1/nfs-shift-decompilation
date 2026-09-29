# Phase 523 — SGB SUMM runtime wrapper mapping

Phase 523 maps the runtime wrapper built by `FUN_006a4900` for SUMM records.

## Proven wrapper

`FUN_006a4900` constructs a 0x38-byte temporary wrapper using concrete vtable `0x00af78ec`.

| SUMM source record field | Wrapper field |
|---|---:|
| `+0x1c` object payload | `+0x08` |
| `+0x0c` resource string | `+0x18` |
| `+0x10` variation palette | `+0x1c` |
| `+0x1a` variation index | `+0x20` |
| `+0x14` scalar | `+0x24` |
| `+0x18` flag bits | `+0x15/+0x16/+0x17` |
| `+0x08` name string | `+0x28/+0x2c` via `FUN_0064eba0` |

`SUMM` and `NODE` therefore converge on the same concrete runtime wrapper class, while their record containers remain distinct.

## IR

`src/scene/sgb_runtime.py` now exposes `runtime_wrapper` for SUMM records with exact source/runtime offsets, wrapper size and hash provenance.

## Boundary

The phase does not normalize the 64-bit name hash algorithm or assign semantic names to the flag bits.