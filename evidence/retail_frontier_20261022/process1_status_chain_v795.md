# Original-PE status chain trace, v795

## Run identity and limits

This was a bounded replay of the original Need for Speed SHIFT PC retail 1.02
PE32 x86 executable in the Linux P-code guest runtime, not a recompiled game
or native Windows/Wine launch.

- `SHIFT.exe` SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`
- Game-data set: `pcode-game-data-v661`
- Startup supplement manifest SHA-256:
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Run: 360 host frames, exit code 0, 1,746,814 P-code dispatches, 4,733
  unique functions, zero Vulkan validation errors.
- The selected target trace had 774 events and was not truncated. It observed
  five workers waiting and one runnable at the final snapshot. The main guest
  entry point remained incomplete, with current function `0x007DA290`.
- `guest_draw_translation=false` and `retail_rendering_proven=false`. This
  run proves no visible retail menu, native game launch or race entry.

Log SHA-256:
`8d924a0c0db3d7684cba32e7c395cde092bfda3f550724cabe71e026e42cbf17`.
Summary JSON SHA-256:
`c822966857c09ed9dd9baebc50d67166ef924cd86f3fba53c55e55a2f0271481`.

## One complete observed status path

At dispatches 461313–462117, the original virtual query wrapper called
`0x00508C70` for item `I=0x27DFAD78`; that callback returned EAX `5`. The
callback called `0x00634F50`, which returned `0`; the nested calls to
`0x0065EC50`, `0x0065FA60` and `0x00653480` also returned `0`. Inside
`0x00653480`, the trace observed `0x00635E40` return `0`, followed by both
main-path tail calls: `0x0065F490` returned pointer `0x27F7C1A0`, and
`0x0066BAB0` returned `1`. The original `0x00653480` body forces its own
return EAX to zero after those calls. This is the main initialization branch,
not the early `0x00651EE0` status-forwarding branch.

| Dispatch | Original target | Caller / return EIP | Observed EAX |
|---:|---|---|---:|
| 461313 | `0x00508C70` | `0x005088A0` / `0x005088AA` | `5` |
| 461816 | `0x00634F50` | `0x00508C70` / `0x00508DF8` | `0` |
| 461943 | `0x0065EC50` | `0x00634F50` / `0x00634F6F` | `0` |
| 461946 | `0x0065FA60` | `0x0065EC50` / `0x0065EC8F` | `0` |
| 462098 | `0x00653480` | `0x0065FA60` / `0x0065FB12` | `0` |
| 462099 | `0x00635E40` | `0x00653480` / `0x006534A7` | `0` |
| 462100 | `0x0065F490` | `0x00653480` / `0x00653539` | `0x27F7C1A0` |
| 462102 | `0x0066BAB0` | `0x00653480` / `0x00653545` | `1` |

Three more calls to `0x00508C70` were observed at dispatches 1,309,960,
1,320,296 and 1,614,531; each returned `5`. For all four recorded
`0x00508C70` invocations, the selected trace also observed `0x00634F50`
return `0` and the status callback return `5`. The complete nested target
chain above is shown for the first invocation; separate invocations remain
separate events, not one merged call.

Static original-PE reports establish that `0x00508C70` maps a zero return from
`0x00634F50` to status `5`, that `0x00653480` forces zero on its main
initialization path, and that `0x00635E40` is a read-only predicate. The
runtime calls and returns agree with those original-byte conditions. The trace
does not establish the semantic meaning of status `5` or identify a missing
compatibility operation.

## Relation to the readiness observation

Separate v791 evidence observed owner `O=0x27DFA5FC` with
`DWORD[O+0x14]=9`; the original updater then cleared `BYTE[O+0x2D]`. The v793
and v795 status-chain events are distinct observations. No trace here proves
that status `5` caused the nonzero owner count, caused the readiness-byte
clear, or prevented a state transition. Do not force readiness based on this
result.

The next useful investigation is the original item/list lifecycle that could
change the owner count or readiness through a verified path. Until that path
is observed, this status chain does not justify a P-code semantic change.
