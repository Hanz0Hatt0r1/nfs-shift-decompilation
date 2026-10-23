# Original-PE worker wait path, v802

## Run identity and limits

This bounded probe ran the original Need for Speed SHIFT PC retail 1.02 PE32
x86 executable in the Linux P-code guest runtime. It is not a recompiled game
or a native Windows/Wine launch.

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.
- 120 requested host frames, exit 0, status `host-frame-loop`, 813,555 P-code
  dispatches, 3,934 unique functions, zero validation errors.
- Final snapshot: three waiting workers; saved main-thread function
  `0x0054BB20`; `retail_rendering_proven=false` and
  `guest_draw_translation=false`.
- Log SHA-256: `88e05ef0bd289cb88ee342ce2abb9fef579566d3f4f5969eef2850b65881b763`.
- Summary JSON SHA-256:
  `f7b590667b32c2d112e6c022c9e329ef995c02e165ee5356c4a15cd52a0c4ac1`.

The selected call trace used stack-slot sampling only and did not inspect
ECX-relative slots. This avoids the earlier tracer-only low-memory read caused
by sampling `[ECX+offset]` on scalar Win32 API arguments.

## Bounded worker-thread events

The selected trace recorded this sequence on guest thread `65538`:

| Dispatch | Call boundary | Observed result |
| ---: | --- | --- |
| 408003 | `0x00649B10` → `0x006B0F60`, return EIP `0x00649C70`; stack argument `0x27F7CC10` | Entry observed |
| 408005 | `0x006B0F60` → `0x00649770`, return EIP `0x006B0F8A`; stack argument `1` | Wrapper called `KERNEL32.dll!Sleep(1)` |
| 408005 / completion 412833 | `0x00649770` → `Sleep` | Import returned `0`; wrapper returned `EAX=0` |
| 412834 / completion 412835 | `0x006B0F60` → `0x00655190`, return EIP `0x006B0FAD` | Helper returned `EAX=1` |
| 412836 / completion 412838 | `0x006B0F60` → `0x006550A0`, return EIP `0x006B0FBB` | Helper returned `EAX=0x27F7CD00` |
| 412839 | `0x006B0F60` → `0x00655150`, return EIP `0x006B1005` | Entry observed; no matching return record before this bounded run ended |

The static body of `0x006B0F60` directly tests `[param+0xB8]`, calls the
`Sleep(1)` wrapper while that field is zero, and then enters further helper
logic. The trace is consistent with that path for this worker: the sleep
wrapper returned and the routine subsequently called `0x00655190`,
`0x006550A0`, and `0x00655150`. The final call's lack of a paired return in
this log means only that completion was not observed before the bounded run
ended; it does not prove a permanent hang.

## Bounded conclusion

This run proves one worker passed through the `Sleep(1)` call and subsequently
entered the post-wait helper path. It does not show that `0x006B0F60` returned,
that all workers exited, or that frontend/race execution became ready. The
three-worker waiting snapshot varies from v798/v801 and is not itself proof of
forward progress. Counts remain diagnostics, not evidence of gameplay.
