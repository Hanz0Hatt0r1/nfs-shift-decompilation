# Phase 520 — SGB NODE runtime wrapper mapping

Phase 520 maps the runtime wrapper created by `FUN_006a4b40` for each SGB `NODE` record.

## Proven runtime wrapper

`FUN_006a4b40` allocates a 0x38-byte wrapper and finalizes it with vtable `0x00af78ec`.

| Source NODE field | Runtime wrapper field | Evidence |
|---|---:|---|
| record `+0x1c` object payload | `+0x08` | `FUN_0069bc50` result copied to `puVar5[2]` |
| record `+0x0c` resource string | `+0x18` | `FUN_006329e0(puVar5+6, ...)` |
| record `+0x10` variation palette | `+0x1c` | `FUN_006329e0(puVar5+7, ...)` |
| record `+0x1a` variation index | `+0x20` | copied to `puVar5[8]` |
| record `+0x14` scalar | `+0x24` | copied to `puVar5[9]` |
| record `+0x18` bit 0/1/2 | `+0x15/+0x16/+0x17` | explicit bit extraction |
| record `+0x08` name string | `+0x28/+0x2c` | 64-bit result of `FUN_0064eba0` |

The implementation exposes the mapping in `runtime_wrapper` without assigning unproven gameplay semantics to the three flag bits or the 64-bit hash.

## Hash boundary

`FUN_0064eba0` is recorded as the producer of the 64-bit name hash. The IR does not synthesize the hash value until the helper's exact algorithm is independently normalized.

## Verification

`tests/test_sgb_runtime.py` verifies the concrete wrapper vtable and every proven destination offset.

## Boundary

This phase proves the SGB NODE record → runtime-wrapper field mapping. It does not resolve deeper OBJECT/HIERARCHY semantic fields or claim that wrapper flag bit names correspond to a higher-level scene state.