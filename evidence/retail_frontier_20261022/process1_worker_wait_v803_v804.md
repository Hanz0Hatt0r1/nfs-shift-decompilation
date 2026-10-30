# Original-PE worker wait follow-up, v803–v804

## Run identity and limits

Both probes executed the original Need for Speed SHIFT PC retail 1.02 PE32
x86 binary in the Linux P-code guest runtime with the same pinned module
manifest. They are not recompiled-game or native Windows/Wine runs.

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.
- v803: 360 frames, status `host-frame-loop`, 1,744,921 P-code dispatches,
  4,733 unique functions, zero validation errors, four workers waiting at the
  final snapshot. Log SHA-256:
  `4cdf6ee6dafd6590c182b98ec249acacdcc779d9be1bd6cd6ba0d282e0a2bd30`;
  summary JSON SHA-256:
  `a4984eece3fe12d7161ce82a542eb288c092b46b62f123b0ff66e74bba35d9a0`.
- v804: 360 frames, status `host-frame-loop`, 1,742,635 P-code dispatches,
  4,733 unique functions, zero validation errors, five workers waiting at the
  final snapshot. The saved main-thread function was `0x00633A50`. The bridge
  reported `guest_draw_translation=false` and `retail_rendering_proven=false`.
  Log SHA-256:
  `e328f5416abe05cdd891fb5f29582e26e04a1c908ae2629770367cc150f10b9f`;
  summary JSON SHA-256:
  `278e7fc6413e242355401f35951d1e309e90cb2e1c985aa9f396db6a24403eb6`.

Both runs used stack-slot sampling only for selected calls. Neither selected
ECX-relative caller/target slots.

## Same-worker sequence in v804

On guest thread `65538`, the selected imports and calls recorded this path:

1. At dispatch 408002, `0x00649B10` entered `0x006B0F60` with stack argument
   `0x27F7CC10`.
2. At dispatch 408003, `0x006B0F60` called `0x0064F530`; the wrapper entered
   `KERNEL32.dll!SetEvent` with handle `0x00060014`, which returned `1`.
3. At dispatch 408004, `0x006B0F60` called `0x00649770` with argument `1`;
   that wrapper entered `KERNEL32.dll!Sleep(1)`. The import returned `0` at
   completion dispatch 412832, and the wrapper returned `EAX=0`.
4. The routine then called `0x00655190`, which returned `EAX=1`, and
   `0x006550A0`, which returned `EAX=0x27F7CD00`.
5. At dispatch 412838, `0x006B0F60` entered `0x00655150`. Its outgoing path
   called `0x0064F540`, which entered
   `KERNEL32.dll!WaitForSingleObjectEx` with handle `0x00060018`, timeout
   `0xFFFFFFFF`, alertable flag `1`, and return EIP `0x006B1005`. No paired
   return from that import or helper appears before the bounded run ended.

Across the entire selected v804 import trace, `SetEvent` handles were
`0x60000` (7 calls), `0x6000C` (5), `0x60010` (5), `0x60014` (1), and
`0x60030` (1). There was no observed `SetEvent(0x60018)` during that run.
Other synchronization APIs, later signals, and activity outside this bounded
window remain possible.

The v803 360-frame run independently observed the same thread enter
`0x00655150` after `Sleep(1)` and had no matching return record for that call
by the end of the run. This repeated absence supports that the helper remains
in its wait path over the tested interval; it does not prove a permanent hang
or a broken scheduler. Waiting workers may be expected while another thread
has not signaled their wait object.

## Bounded conclusion

The v520 “resumed but predicate bit 2 remains clear” symptom was absent from
the observed v798 paths. v804 now shows that one later worker path reaches a
real `WaitForSingleObjectEx(..., INFINITE, TRUE)` call after its one-shot
`Sleep(1)` path. This evidence localizes the bounded wait but does not identify
the producer of handle `0x60018`, prove the wait is erroneous, or establish
frontend readiness or race entry. No P-code or Win32 semantics were changed.
