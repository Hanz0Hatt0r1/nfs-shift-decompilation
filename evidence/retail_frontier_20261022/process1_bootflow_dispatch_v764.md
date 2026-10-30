# Process 1 — BootFlow dispatch frontier, v764

## Run identity and result

- Original SHIFT PC retail 1.02 PE32 SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Runtime binary SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`.
- P-code overrides and supplements: hash-checked from the recorded v759 module evidence.
- Game data: `pcode-game-data-v661`.
- Trace log SHA-256: `ab34e548c29900d1604b2f8bbf5228c87f8a2242e4615421793619bb389abeb7`.
- Result: `host-frame-loop`, 360 host frames, 1,750,262 P-code dispatches, 4,729 unique functions, zero Vulkan validation errors.
- Guest-call trace and UI-gate trace were enabled and not truncated.

This is a Linux P-code guest run of the original retail PE, not a native Windows/Wine launch.

## Selected state-dispatch observations

| Retail target | Count | Caller(s) | Observed return |
|---|---:|---|---|
| `0x0054AEA0` (BootFlow init method) | 1 | `0x00508860` | `0` |
| `0x0054AF30` (BootPhaseMain method) | 0 | — | — |
| `0x0054B070` | 0 | — | — |
| `0x0040E460` (GUI setup path) | 0 | — | — |
| `0x005459F0` (callback registration path) | 0 | — | — |
| `0x0050CD90` (callback pointer setter) | 0 | — | — |
| `0x0054BE00` | 1,120 | `0x0040BA50` | `1` |

For reference, original `.rdata` at `0x00ACC57C` begins the BootFlow vtable. The DWORD at `0x00ACC590` (`+0x14`) is `0x0054AF30`. Ghidra's `FUN_0054AEA0` initialization records the `BootFlow` name and the `Game` phase. These static facts identify the table entry; the trace shows only that this entry was not dispatched during the measured interval.

The 1,120 calls to `0x0054BE00` also produced 1,120 UI-gate calls to `0x0050CEB0`. Every observed gate state word and callback object was zero, the helper flag was `0x00`, and the gate returned zero. The gate trace was not truncated. The replay did not enable write-provenance tracing, so null last-writer fields are not treated as proof of no writer.

## Bounded conclusion

The active P-code scheduler initializes the BootFlow state once, but the sampled 360-frame interval does not dispatch BootPhaseMain, the GUI setup path, or the callback-pointer setter. During the same interval a different update target repeatedly checks the UI gate, which remains closed. This is the current P1 state-transition/runtime blocker to investigate. No guest state was forced.

The bridge still reports `guest_draw_translation=false`; the run does not prove a rendered menu, retail draw, gameplay or race entry. The target counts and host-frame count are bounded runtime observations, not global reachability claims.
