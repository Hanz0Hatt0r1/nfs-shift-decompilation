# Process 1 nested DrawIndexedPrimitive frontier trace — v756

Date: 2026-10-22

## Run identity and result

This was a controlled replay of the original SHIFT retail PE32 inside the Linux P-code guest runtime, not a native Windows or Wine launch.

- PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`
- Module manifest: `module-manifest-v659-005a0ef0.json`, SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Game data: `pcode-game-data-v661`
- Trace log SHA-256: `6f9351e5bef68e132ad9780e42e8031c9566ebdc61d37f39730435441863a50e`

The replay completed 360 host frames with no reported blocker and zero validation errors. A full, untruncated guest call trace selected `0x00852760`, nested methods `0x00850F10`, `0x00851730`, and `0x008521F0`, adapter `0x0084FD60`, and all four D3D9 Draw/DrawUP imports. The trace contained zero events. The bridge reported 360 clear and 360 present submissions, with `guest_draw_translation=false`.

## Interpretation and limits

This is a bounded negative observation for the tested replay only. None of the selected methods or imports were reached. That narrows the observed execution frontier to before this render path in this run, but does not prove that the retail path is unreachable in other UI states. Dispatch and frame totals are context only; they do not prove game launch, frontend readiness, retail drawing, or gameplay.

See the [machine-readable trace](process1_nested_draw_v756.json) and the separate [static retail path analysis](process1_nested_draw_static_00852760.md).
