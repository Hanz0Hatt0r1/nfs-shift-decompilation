# Original-PE worker scheduler evidence, v798–v801

## Run identity and limits

Both runs executed the original Need for Speed SHIFT PC retail 1.02 PE32 x86
inside the Linux P-code guest runtime with the pinned module manifest. They
were bounded 120-host-frame probes. Neither is a recompiled game or a native
Windows/Wine launch.

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.
- v798: exit 0, `host-frame-loop`, 120 frames, 814,921 P-code dispatches,
  3,934 unique functions, zero validation errors, two workers waiting at the
  final snapshot. Runtime SHA-256:
  `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.
  Log SHA-256: `875381a505ecd821f7f93cdd80aaa961fbc49b7ff894bed811e3ee69c2fac622`;
  summary JSON SHA-256:
  `c26875afe90481ba3548c512c198c8ac5483ba8189638eea115fb7b0c6b9373b`.
- v801: exit 0, `host-frame-loop`, 120 frames, 813,930 P-code dispatches,
  3,934 unique functions, zero validation errors, two workers waiting at the
  final snapshot. The report's saved main-thread function was `0x00509551`.
  Log SHA-256: `759111830ac0f52b9ae27f3429de5f2f26539c8304d58af330bfb7a9a3fd7ea7`;
  summary JSON SHA-256:
  `49d7286ad13b6b4018637be7eccfc9978339c8250bd9eaf6ee0445b1d97ffc1d`.

The bridge reported `retail_rendering_proven=false`. These runs do not prove a
visible retail menu, race entry, or end-to-end game launch. Dispatch and
function counts are diagnostic only.

## Worker state and predicate observations

The v798 targeted trace recorded `0x00649CB0` write the value `2` to each of
four observed state words:

| Dispatch | Address | Value | Caller subsequently observed |
| ---: | --- | ---: | --- |
| 390809 | `0x27F39964` | `2` | `0x006496F0` returned `1` at 390813 |
| 395647 | `0x27F399E4` | `2` | `0x006496F0` returned `1` at 395651 |
| 406658 | `0x27F39A64` | `2` | `0x006496F0` returned `1` at 406663 |
| 412779 | `0x27F39AE4` | `2` | `0x006496F0` returned `1` at 412784 |

Two later calls to predicate `0x006550F0` returned `1`. At dispatch 462105,
the checked wrapper pointed at `0x27F398F0`, whose `+0x74` word had last been
written as `2` at `0x27F39964`. At dispatch 601967, the wrapper pointed at
`0x27F39970`, whose `+0x74` word had last been written as `2` at
`0x27F399E4`. This verifies the checked state bit was set on these two
observed paths. It does not claim that all worker predicates or all worker
objects were checked.

## Win32 import observations

The corrected v801 import-only trace, with no ECX-relative caller/target slot
sampling, recorded four `KERNEL32.dll!CreateThread` calls returning handles
`0x80000`, `0x80010`, `0x80020`, and `0x80030`. Four corresponding
`KERNEL32.dll!ResumeThread` calls through `0x006496F0` returned `1`. It also
recorded one `WaitForSingleObject` call returning `0`, one worker
`Sleep(1)` returning `0`, and 591 `SwitchToThread` entries (590 returned `1`,
one returned `0`). The bounded run completed its host-frame loop after these
events.

An earlier diagnostic configuration combined imported-target tracing with
ECX-relative slot offsets. It attempted to inspect `[ECX+0x74]` during
`Sleep(1)`, where `ECX=1`, and the tracer itself raised a reserved-low-memory
read at `0x75`. That failure was instrumentation-induced, not a guest P-code
fault. The corrected v801 configuration omitted caller/target slots and
completed successfully.

## Bounded conclusion

The old v520 symptom—successful `ResumeThread` followed by a worker predicate
bit remaining clear—does not persist for the four state writes and two
predicate checks observed in v798. v801 independently records four successful
thread resumes and the same 120-frame host loop. This narrows the scheduler
investigation; it does not establish complete worker lifecycle correctness or
explain the remaining frontend/race blockers. The next runtime blocker must be
selected from the latest retail frontier and its exact failure evidence, not
from dispatch totals.
