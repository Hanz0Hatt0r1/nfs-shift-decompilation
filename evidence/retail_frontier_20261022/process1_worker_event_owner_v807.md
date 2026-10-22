# Original-PE worker event owner trace, v807

## Run identity

v807 ran the original Need for Speed SHIFT PC retail 1.02 PE32 x86 executable
in the Linux P-code guest runtime. It was not a recompiled-game or native
Windows/Wine run.

- Retail PE SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256:
  `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256:
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- 600 host frames; `host-frame-loop`; 2,421,409 P-code dispatches;
  4,738 unique functions; zero Vulkan validation errors; four guest workers
  waiting at the final snapshot. The main-thread function snapshot was
  `0x0082C9F0`.
- Clear/present requests: 1,460 / 1,458; Vulkan submissions: 600 / 600.
  `guest_draw_translation=false` and `retail_rendering_proven=false`.
- Probe log SHA-256:
  `158296dbc381912bae2eb158df08a32e9f00518de80f7e34ef69d8d6fccc239c`
- Summary JSON SHA-256:
  `6a64af1656f19997c700176cdacf8897d7e9be8cc7d7cde79bdb3f552faa3b99`

## Event owner and queue observations

Worker `0x00010002` created event handle `0x00060018` at dispatch 407,915 via
`CreateEventW` with four zero arguments. The call entered through wrapper
`0x0064F570` with `ECX=0x27F7CD40`, the event field at owner
`0x27F7CD00 + 0x40`. At dispatch 412,840, the same worker entered
`0x0064FE50` from `0x00655150` with `ECX=0x27F7CD00`; sampled owner fields
were `+0x40=0x60018`, `+0xC0=0xF`, `+0xB4=0`, and `+0xB8=0`. The next
dispatch entered `WaitForSingleObjectEx(0x60018, INFINITE, TRUE)`. The wait
had no recorded return by the end of the run.

The selected trace recorded 25 `SetEvent` calls, none for `0x60018`. It also
recorded calls to `0x00650350` from `0x006880C0` on two different owners:
`0x27F7C290` with event `0x6000C`, and `0x27F7C780` with event `0x60010`.
The selected `SetEvent` calls targeted those handles eight times each. No
retained `0x00650350` call used owner `0x27F7CD00`; the selected call trace was
not truncated.

This shows queue activity and event signaling for two other owner objects
while the `0x60018` owner remained in an indefinite wait. It is consistent
with an idle worker queue, but does not establish that this queue should have
received work or that its producer was absent outside the selected trace. It
does not demonstrate a scheduler defect, a guest state mismatch, a visible
frontend, or race entry. No event was synthesized and no guest state was
changed.

## Next evidence target

Trace the producer/queue mutations for owner `0x27F7CD00`, or establish from
the original PE whether this worker is expected to remain idle. Preserve the
existing event and scheduler semantics until that ownership contract is
established. The v806 and v807 raw logs remain outside Git; their hashes above
identify the bounded observations.
