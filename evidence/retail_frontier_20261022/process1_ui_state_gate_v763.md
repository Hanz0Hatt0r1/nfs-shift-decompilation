# Process 1 — retail UI state-gate frontier, v763

## Run identity

- Original SHIFT PC retail 1.02 PE32 SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Local runtime binary SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`.
- The P-code override/supplement set was reconstructed from the v759 recorded module evidence and hash-checked by the existing retail probe loader.
- Game data: `pcode-game-data-v661`.
- v763 trace log SHA-256: `9255d0656846fa0e2799a972d3d2742373a71f200f6a50bab3e180e193937ebe`.
- Bounded interval: 360 host frames; `SHIFT_TRACE_UI_STATE_GATE=1`; selected D3D9 Draw/DrawUP imports; selected targets `0x005459F0` and `0x0050CD90`.

The original retail PE ran inside the Linux P-code guest runtime. This is not a native Windows/Wine launch.

## Observed gate state

The untruncated trace contains **1,123 calls** to retail UI gate `0x0050CEB0`, with matching helper `0x0050C880` entries. Across those calls:

- gate state word: `0x00000000`;
- callback object: `0x00000000`;
- helper flag byte: `0x00`;
- gate return EAX: `0x00000000`.

The trace did not observe the callback branch becoming active during this interval. Writer attribution fields were not captured because guest-write provenance tracing was not enabled; therefore null last-writer fields are not used as proof that no writer exists.

The same replay selected the four D3D9 Draw/DrawUP imports (`DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`) and the callback registration targets `0x005459F0` / `0x0050CD90`. The guest-call trace was not truncated and contained **zero events** for those selections. The Vulkan bridge reported 360 clear submissions and 360 present submissions, with `guest_draw_translation=false`.

## Bounded interpretation

Static Ghidra export shows a callback-registration path in which `FUN_005459F0` calls setter `FUN_0050CD90`; its caller chain includes `FUN_0040E460`, which is called by `FUN_0054AF30` (`BootPhaseMain: Load Done`). A separate 360-frame probe v761 also selected `0x0054AF30`, `0x0040E460`, `0x005459F0`, and `0x0050CD90` and recorded no selected-target events; its log SHA-256 is `07b15fb0ed4d1d18e47bd0681cae6129956de441df91225b3a1246e3c11721f1`.

These are bounded observations, not proof of global unreachability. They establish that the callback registration path was not observed during these probe intervals while the active gate repeatedly returned zero. They do not prove why the BootPhaseMain path did not run, whether another UI state can initialize the callback, that a menu was rendered, or that race entry is reachable. Dispatch counts and host frames are context only.

## Current next evidence target

Trace and classify the retail BootPhaseMain state dispatch path that reaches `0x0054AF30`, including its owning vtable/state transition, so the callback setter path can be reached through original initialization rather than by forcing guest state. Keep the v761/v763 no-event results bounded to their recorded intervals.
