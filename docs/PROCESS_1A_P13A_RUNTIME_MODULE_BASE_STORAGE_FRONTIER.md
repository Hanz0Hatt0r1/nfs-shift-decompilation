# Process 1A / P1.3A — runtime module-base storage frontier

## Scope

After the bounded on-disk carrier seed surface and exact `imagebase + carrier RVA` immediate form were closed, runtime persistence of the preferred module base itself remained a concrete reconstruction seed.

This pass follows the exact `0x00400000` startup argument through the PC-retail machine code. It does not claim downstream consumers are exhausted.

## Machine result

`___tmainCRTStartup` pushes `0x00400000` at `0x00904817` and calls `FUN_00a69160` at `0x0090481c`.

The runtime receiver used by `FUN_00a69160` is exact:

- `FUN_00886980` returns global `0x00c29634`;
- startup setup at `0x00886a66` obtains the fixed object from `thunk_FUN_0040b870` and stores it to `0x00c29634`;
- `FUN_0040b870` returns fixed object `0x00bbf960` and constructs it through `thunk_FUN_00d33990`;
- constructor body `0x00d339b0` stores exact vptr `0x00aab2d8`.

That vtable resolves the two module-base setter calls in `FUN_00a69160`:

- slot `+0x80` = `FUN_00886b70`; it forwards incoming `EDX` through `FUN_006347e0`, which stores the argument at fixed singleton `0x00bfa4f8+0x4` (`0x00bfa4fc`);
- slot `+0xa0` = `FUN_00886c60`; it stores incoming `EDX` directly to fixed singleton `0x00bfa4f8+0xc` (`0x00bfa504`).

The same vtable exposes getters:

- slot `+0x84` = `FUN_00886c00` -> singleton `+0x4`;
- slot `+0xa4` = `FUN_00886c70` -> singleton `+0xc`.

Therefore runtime persistence of the module base is **positive and bounded to two proven fields**. The stored value remains exactly the module base, not a canonical P1.3A carrier entrypoint.

## Gate

```text
startup module-base storage subset complete = true
runtime module-base persistence found        = true
proven storage fields                        = 2
stored fields already carrier pointers       = false
getter/consumer paths complete               = false
manual imagebase+RVA reconstruction complete = false
callback registration ruled out              = false
incoming indirect entry ruled out            = false
slot0 / slot1 / P1.3 complete                = false
provider count                               = 7
```

## Next step

Trace consumers of the `+0x84/+0xa4` getters and classify any arithmetic that combines either stored module base with RVA/table data or registers the result as a callback. Continue selected-wheel data-pointer persistence independently.
