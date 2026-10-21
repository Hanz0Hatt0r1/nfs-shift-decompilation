# Process 1 — retail display consumer trace (2026-10-21)

## Run

The bounded v692 run used the original retail PC `SHIFT.exe` PE32 image
(SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`)
inside the recompiled guest P-code runtime. The runtime binary SHA-256 was
`d46ea64435ed73d9e799d37e7ce219238d780bde7b251d6f2e9666962bd88cb8`.
This was not a native Windows launch of `SHIFT.exe`.

The run completed 360 requested host frames, 1,738,845 P-code dispatches and
4,729 unique functions, with three workers waiting, no validation errors and
no current blocker. It recorded 1,112 D3D9 clear requests and 1,111 present
requests, but only host-side bridge submissions. `guest_draw_translation` and
`retail_rendering_proven` remained false.

The bounded live trace watched `0x00831380`, `0x005e1d50`, `0x00835590` and
four D3D9 Draw* imports. Its raw log is local-only; SHA-256
`a2bdcdd676ed083ee76697ba34e4bb287b282d73201ec705b44503937f7ee51d`,
4,069,724 bytes. The compact call counts and run summary are in
[`ui-event-path-v692.json`](../evidence/retail_frontier_20261021/ui-event-path-v692.json).
No selected Draw* import call was present.

## Observed consumer path

The exact retail PE bytes at `0x00835590` show this sequence:

```text
008355b5 call 00831380
008355ba mov esi,[ebp-8]
008355bd lea ecx,[esi+4]
008355c0 call 005e1d50
008355c5 cmp eax,1
008355c8 jne 008355e7
008355d0 call 008352f0
```

The getter at `0x005e1d50` is `mov eax,[ecx]; ret`. In the v692 trace,
`0x00831380` returned 660 times to `0x00835590`; the output dword read after
return was `0x3f800000` each time. The following getter ran 660 times with
`ECX=0x3f800004` and returned `EAX=0` each time. Given the exact `cmp` and
`jne` bytes, the zero result takes the branch to `0x008355e7`, skipping the
later `0x008352f0` call in each recorded iteration. This is a local control-flow
result, not a complete explanation of why the path has no observed Draw* call.

The runtime reserves a flat four-gigabyte PE32 guest address range, and the
trace's `target+0` read is diagnostic. It does not model Win32 page commitment
for that address. Thus the zero result does not establish whether the original
Windows process would read a valid zero or fault at `0x3f800004`. The payload
`0x3f800000` is also not enough to assign a pointer or float type. The next
step is producer/type provenance and, if available, a page-validity-aware
comparison against the original process; do not rewrite the branch or substitute
a value from this evidence alone.

## Audio hypothesis

This v692 trace specifically targeted D3D9 Draw* imports; it is not an audio
trace. The separate bounded v667 probe watched selected WinMM/MSACM and module
lookup APIs and did not observe them through 360 host frames. That makes a
missing selected audio import an unlikely explanation for the v667 horizon,
but does not rule out audio APIs or callbacks on later frontend/gameplay paths.
See [`PROCESS1_AUDIO_IMPORT_PROBE_20261021.md`](PROCESS1_AUDIO_IMPORT_PROBE_20261021.md)
for that probe's limits and the unresolved v520 causality question.

## Limits

- This is recompiled P-code execution over the retail PE, not evidence that the
  original retail executable reached the frontend or race.
- Host-frame, dispatch and function counts are diagnostics, not game-launch or
  gameplay proof.
- The local getter result narrows the consumer frontier but does not demonstrate
  that the selected branch should have continued, nor a causal edge to D3D9
  drawing.
- No guest value, API result, branch or ordering was changed.
