# Process 1 — UI gate and boot phase frontier, v776

## Run identity

- Original SHIFT PC retail 1.02 PE32 SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Runtime SHA-256: `4d5e118b93567f9e31f076edcb5c1e1d97f3543222d703d2b26fca8056346ee8`.
- Verified module manifest: v659.
- Bounded interval: 360 host frames with validation enabled.
- Trace log SHA-256: `072db93ef07c2104e23cd5973709ff8eb501df20754de9a7e731ab3147d68940`.
- Summary JSON SHA-256: `1fbcdda03f4c8ca40b3523bed667b756f40d55dee2a9b0520905be1b38c2c4b7`.
- This was the original retail PE running in the Linux P-code guest runtime, not a native Windows or Wine launch.

## Bounded observations

- Result: `host-frame-loop`, 360 frames, zero validation errors.
- The UI-gate trace contains **1,124 complete calls** to `0x0050CEB0`, all called from `0x0054BE00`. Across them the observed gate word and callback object are zero; helper byte and gate return are zero. The callback target is null on every sampled event.
- This run did not enable guest-write provenance. Null last-writer fields therefore do not establish that no setter ran elsewhere.
- The selected guest-call trace for `0x0054AF30`, `0x0040E460`, `0x005459F0`, and `0x0050CD90` contains zero events and is not truncated.
- At the final snapshot the main thread is runnable in `0x007E3E20`, with active call stack `0x0090488A → 0x009046AA → 0x00A69160 → 0x0040BA50 → 0x0054BE00 → 0x00427770 → 0x007DC990 → 0x007DA290 → 0x007F3AF0 → 0x007DA290 → 0x007DA290 → 0x007E4850 → 0x007E3E20`. Six worker threads were registered: four waiting and two runnable.
- The D3D9 bridge submitted 360 clears and 360 presents; it reported 1,126 clear requests, 1,124 present requests, and 764 pending presents. `guest_draw_translation=false` and `retail_rendering_proven=false`.

## Interpretation and limits

The bounded replay again observes the active update checking a closed UI gate while the selected BootPhaseMain/setup/registration path is not observed. It does not establish why that path is not dispatched, whether a different UI state would register the callback, or that the zero gate causes the missing frontend. It does not prove a rendered menu, retail draw, or race entry. Host frames and P-code dispatch totals are context, not evidence of game launch.

This is a new observation only. No guest state was forced and no implementation was changed for this probe. The next useful investigation is the owning retail state transition that would dispatch `0x0054AF30`, preserving original initialization semantics.
