# Retail startup pool request origin — 2026-10-18

This is a static follow-up to runtime probe v66; it does not claim a v67
runtime probe.

## Evidence

The v66 retail probe ends after 61,307 dispatches across 1,325 functions. Its
large allocation request is `0x0f2bcec8` (254,529,224 bytes), with flags
`0x80`. `FUN_00638020` tries `Base System`, `Game`, `Overflow`, and `FMOD`;
none returns an allocation. The list head inspected for each pool contains a
first word below the request:

| Pool | Pool object | First selected node | First word |
| --- | --- | --- | ---: |
| Base System | `0x10001c18` | `0x27f87528` | `0x00000120` |
| Game | `0x100021b8` | `0x36266000` | `0x09f146d8` |
| Overflow | `0x10002398` | `0x36cd4000` | `0x00993f88` |
| FMOD | `0x10002578` | `0x3a8d4000` | `0x03b826d8` |

For the selected Base System list, the five-node `+0x10` chain ends at
`0x27f88dbc`; its largest first word is `0x07beed0c`. These are the raw
values read from the allocator's compared field. Other node words remain
unclassified. Full captures are in the [v65 attempt log](recompiled_pcode_android_retail_frontier_v65_pool_fallback_attempts_20261018.log)
and [v66 list log](recompiled_pcode_android_retail_frontier_v66_pool_fallback_lists_20261018.log).

The v66 call stack identifies the request origin. `FUN_006382b0` receives the
request through the tail-call wrapper at `0x00886900`; its stack return address
is `0x0062f352`, immediately after the call to that wrapper in `FUN_0062f2d0`.
The captured frame for `FUN_0062f2d0` reports stack words
`0x27f324bc, 0x00000000, 0x00aabee0`. At runtime, the wrapper frame has
`EBX=0x0a2d6a10`, `ESI=0x04fe64b8`, and request size `ECX=0x0f2bcec8`.
Retail instructions in `FUN_0062f2d0` multiply a stack value by a value read
through its second stack argument, compute additional alignment/bitmap space,
then pass the total to `0x00886900`. The observed allocator size matches the
sum of the two captured terms, rounded to four bytes.

An upstream caller provides a more specific lead. In `FUN_00d8a600`, the
instruction at `0x00d8a6b8` loads `ECX` from `[ESI+0x18]` and calls
`FUN_0062f6f0`. The v66 frame has `ESI=0x00bdb560`, and its captured object
words show `[0x00bdb560+0x18] == 0`. `FUN_0062f6f0` then calls
`FUN_0062f2d0` on the path that allocates its backing storage. The origin is
therefore consistent with a missing/null nested object feeding the oversized
request; the evidence does not yet identify which earlier initialization or
P-code path first left that field null.

## Runtime correction

The guest RAM model reserved four gigabytes and accepted every in-range
address, including the low 64 KiB. That allowed a null-derived pointer in this
path to read mapped host-backed bytes and continue into allocator code. The
runtime now rejects guest RAM reads and writes below `0x00010000`, and Win32
pointer validation applies the same lower bound. The check follows the
minimum-application-address contract exposed by Windows `SYSTEM_INFO` and the
existing PE32 loader's minimum image address.

Local verification passed for the native runtime build, the P-code module
CTest, and the focused P-code exporter/runtime pytest set. A full retail probe
after this correction is still pending: the generated
`libnfs_shift_pcode_startup_20261018.so` input is not present in the local
workspace; the latest listed GitHub Actions artifacts are only Linux smoke and Win32 proxy bundles. No v67 runtime result is
claimed.
