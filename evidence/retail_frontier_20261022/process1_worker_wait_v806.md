# Original-PE worker event wait, v806

## Run identity

v806 ran the original Need for Speed SHIFT PC retail 1.02 PE32 x86 executable
in the Linux P-code guest runtime. It was not a recompiled-game or native
Windows/Wine run.

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256:
  `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256:
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- 600 frames; status `host-frame-loop`; 2,420,968 P-code dispatches;
  4,738 unique functions; 600 host frames rendered; zero Vulkan validation
  errors; two guest workers waiting at the final snapshot. The main-thread
  function snapshot was `0x005093A0`.
- Runtime summary JSON SHA-256:
  `39de134d9a0bd98cc0340a0d8e570c8e247d1ef8e2e47429712e36123f967673`
- Probe log SHA-256:
  `2b02822c0c6e2573cb50bd87141d3d571a969940e5d720d898e8496abbcae7f4`

## Event observation

The selected import trace records thread `65538` creating event `0x60018` at
dispatch `407915` through `CreateEventW` with all four stack arguments zero.
The same worker entered `WaitForSingleObjectEx` at dispatch `412841` with
handle `0x60018`, timeout `0xFFFFFFFF`, and alertable flag `1`. There is no
matching return from this wait in the 600-frame log.

The selected synchronization-import set recorded 19 `SetEvent` calls. Their
handles were `0x60000` (7), `0x6000C` (5), `0x60010` (5), `0x60014` (1), and
`0x60030` (1); none targeted `0x60018`. These selected events match the
corresponding v805 wait/create sequence. This evidence establishes only that
the observed event remained unsignaled in the selected trace during this
bounded interval. It does not prove that the worker should already have been
released, exclude an unselected signal path, or show a scheduler defect.

## Limits

The guest completed its bounded host-frame loop with zero validation errors,
but that is not evidence of a visible retail menu or race. The summary's clear
and present submission counts and `guest_draw_translation` diagnostic are not
proof of original guest draw translation, rendered game content, or readiness.
No guest state was forced and no Win32 event semantics were changed.
