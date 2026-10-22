# Original-PE worker wait-object creation, v805

## Run identity

This 360-frame probe executed the original Need for Speed SHIFT PC retail 1.02
PE32 x86 executable in the Linux P-code guest runtime with the pinned manifest.
It is not a recompiled-game or native Windows/Wine launch.

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.
- Status `host-frame-loop`, 360 frames, 1,743,184 P-code dispatches, 4,733
  unique functions, zero validation errors, four workers waiting at the final
  snapshot. `guest_draw_translation=false` and `retail_rendering_proven=false`.
- Log SHA-256: `053c48d0fa2be00ee6ba4c271d32d9886eecb3fed9e7ade27254a05af8b7b377`.
- Summary JSON SHA-256:
  `1d4f7fd12ceeb71f16e6c3a1099da519054949dbea8b5cd0e4d1bd42088bc671`.

## Worker 65538 event sequence

The import trace records these exact events:

1. At dispatch 407915, thread `65538` called `KERNEL32.dll!CreateEventW`
   through wrapper `0x0064F570`, returning handle `0x00060018`. Its four
   stack arguments were all zero: null security attributes, `bManualReset=0`,
   `bInitialState=0`, and null name. Under Win32 `CreateEventW` semantics,
   this is an unnamed, auto-reset event initially nonsignaled.
2. At dispatch 408004, the worker called `SetEvent(0x00060014)`, which returned
   `1`, then entered `Sleep(1)` and completed that wait by dispatch 412832.
3. After the wait-path helpers, at dispatch 412841 the same thread called
   `WaitForSingleObjectEx(0x00060018, 0xFFFFFFFF, 1)` through `0x0064F540`.
   No matching return for this wait was recorded before the 360-frame run
   ended.
4. Across the selected v805 imports, `SetEvent` was called for handles
   `0x60000`, `0x6000C`, `0x60010`, `0x60014`, and `0x60030`; there was no
   `SetEvent(0x60018)` in this bounded run.

The same sequence was seen in v804: the worker waited on `0x60018` and no
selected `SetEvent` targeted it before that probe ended. This supports a
bounded, unsignaled wait in the tested interval. It does not prove the event
should already have been signaled, exclude other synchronization APIs, or
identify the producer expected to set it.

## Conclusion and limits

The worker is not merely remaining in the initial `Sleep(1)` poll: it creates
an initially nonsignaled event and subsequently waits on that event
indefinitely. The runtime trace does not establish whether this handshake is
normal, whether another callback should signal it later, or whether any
wait-state mismatch is caused by guest scheduling. Do not add a synthetic
signal or alter original Win32 semantics based on this bounded evidence.

The existing focused `shift_runtime_recompiled_pcode_module` regression
includes an alertable event wait that resumes after a guest worker signals it;
it passed in this checkout, as did `shift_runtime_body_feedback_scheduler`.
That verifies the fixture's scheduler/event path, not the retail producer for
handle `0x60018`.
