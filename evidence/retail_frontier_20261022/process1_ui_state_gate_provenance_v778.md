# Process 1 — UI gate write provenance, v778

## Run identity

- Original SHIFT PC retail 1.02 PE32 SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Runtime SHA-256: `4d5e118b93567f9e31f076edcb5c1e1d97f3543222d703d2b26fca8056346ee8`.
- Verified P-code module manifest: v659; game data: v661.
- Bounded interval: 120 host frames, validation enabled; UI gate, selected guest calls, and write provenance for `0x00BE250C`, `0x00BE2534`, `0x00BE2548` enabled.
- Result: `host-frame-loop`, exit 0, zero validation errors.
- Trace log SHA-256: `16d57f7de3fd0d523b39b9253534b1c80aca49d6bb26102779e72b706528e3c2`.
- Summary JSON SHA-256: `9167c5eeb22809e2048781d52e2269681537650ffa73325e57714094ee1ce470`.
- This was the original PE running in the Linux P-code guest runtime, not a native Windows or Wine launch.

## Gate observations and last-writer provenance

The untruncated trace contains **592 calls** to gate `0x0050CEB0`, all from `0x0054BE00`. The checked state word at `0x00BE2534`, callback object at `0x00BE2548`, and helper byte at `0x00BE250C` were zero on every gate call; every gate returned zero and no callback target was invoked.

For every sampled call, the runtime's last-writer records were:

- Callback pointer `0x00BE2548`: constructor `0x004EB550` wrote dword zero, with `ECX=0x00BE2500`; it was called from `0x0050D030` (return `0x00545CD5`).
- Gate state word `0x00BE2534`: `0x0062FDE0` wrote dword zero to `this+0x24` of object `0x00BE2510`, on worker thread `0x00173FAC`. It was called by `0x0062FFD0` (return `0x0062FFF6`), in turn under `0x004E8BC0` (return `0x004E8BE3`), reached from `0x0050CF10` (return `0x004EB5B4`).
- Helper flag byte `0x00BE250C`: `0x0050C820` wrote byte zero, called by `0x004EB550` (return `0x004EB559`, caller return `0x00545CD5`).

The selected guest-call trace for `0x0054AF30`, `0x0040E460`, `0x005459F0`, and `0x0050CD90` contains zero events and is not truncated. At the final snapshot the main thread is in `0x00509551` under `0x005093A0`, called by `0x0054BB20`; this 120-frame snapshot differs from the v776 final stack and is not evidence that the selected setup path was reached.

## Interpretation and limits

This run confirms the gate fields are explicitly initialized or last written to zero in the observed execution interval. It does **not** show that the callback setter ran: its selected target was not observed, and the callback pointer's last writer remains the constructor. The zero gate state is refreshed by the sampled worker-side writer, but this does not establish why BootPhaseMain/setup is not dispatched or that the gate causes the missing frontend. The bridge submitted 120 clears and 120 presents, with 593 clear requests, 592 present requests, and 472 pending presents; `guest_draw_translation=false`. No rendered menu, retail draw, race, or race entry is proven.

No guest state was forced and no implementation was changed for this probe. P-code dispatch and host-frame counts are context only.
