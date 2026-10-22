# Process 1 UI callback pointer provenance — v751

Date: 2026-10-22

## Run identity

This was a controlled replay of the original SHIFT retail PE32 image inside the Linux P-code guest runtime. It was not a native Windows or Wine launch.

- PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`
- Module manifest: `module-manifest-v659-005a0ef0.json`, SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Game data: `pcode-game-data-v661`
- Trace log SHA-256: `62f52c07c6ed48e6d8e3e7f3e8d599495213eb4aae9b90c8130c7e4e0e964b61`
- Trace environment: `SHIFT_TRACE_GUEST_PROVENANCE=0x00be250c,0x00be2548`, `SHIFT_TRACE_UI_STATE_GATE=1`

The run requested and rendered 120 host frames, exited with status 0 at the host-frame loop, and reported no runtime blocker. The guest scheduler trace contained 594 calls to `0x0050CEB0`; every call used `ECX=0x00BE2500`, observed state word `0`, callback object `0`, and returned `EAX=0`. The `0x0050C880` helper ran 594 times and returned `EAX=0x00BE2300` each time with helper byte `0`. The child readiness helper `0x0082F3C0` returned `0x00BE2301` on all 594 calls, its truth value indicating `[child+0x24] == 0`.

For each gate event, the last traced writer to `[parent+0x48]` was constructor `0x004EB550`: it wrote dword zero at `0x00BE2548`, with `ECX=0x00BE2500`, called from `0x0050D030` (return address `0x00545CD5`). The last traced writer to `[parent+0x0c]` was base initializer `0x0050C820`, called by `0x004EB550`, which wrote byte zero at `0x00BE250C`.

## Interpretation and limits

The retail instructions explain the observed zero return without changing guest state: `0x0050CEB0` first calls `0x0082F3C0`; when the child readiness predicate is true, it calls `0x0050C880`. That helper sees the zero byte at `parent+0x0c`, takes its early return with low byte zero, and the gate then skips its wait loop. The gate sees a null callback pointer at `parent+0x48`, skips the callback call, and returns zero. This matches all 594 captured calls.

The trace proves that the constructor remained the latest writer to these fields in this run. It does not prove that no later setter or registration path exists elsewhere, nor that such a path is unreachable in other UI states. Do not force either field nonzero based on this evidence.

The run reached the host-frame loop but did not prove frontend readiness, retail draw translation, or an offline race. Its dispatch and unique-function counts are runtime diagnostics, not evidence that gameplay launched. The machine-readable summary is [process1_ui_callback_pointer_provenance_v751.json](process1_ui_callback_pointer_provenance_v751.json).
