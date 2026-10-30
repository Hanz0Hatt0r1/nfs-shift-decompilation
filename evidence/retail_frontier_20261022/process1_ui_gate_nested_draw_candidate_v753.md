# Process 1 nested render-candidate trace — v753

Date: 2026-10-22

## Run identity and result

This was a controlled replay of the original SHIFT retail PE32 image inside the Linux P-code guest runtime, not a native Windows or Wine launch.

- PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`
- Module manifest: `module-manifest-v659-005a0ef0.json`, SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Game data: `pcode-game-data-v661`
- Log SHA-256: `0351c4fcaf91fb1fd8f58aa392c2ba0b99d419775c584cb45a201bd7fa0adade`

The probe requested and rendered 360 host frames, reached `host-frame-loop`, exited 0, and reported no runtime blocker. The guest call trace was enabled and not truncated. It selected target `0x00852760` and all four D3D9 Draw/DrawUP imports (`DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`); the trace contained zero events. The bridge still recorded `guest_draw_translation=false`, with 360 clear submissions and 360 present submissions.

## Interpretation and limits

This is a bounded negative observation: the selected target and Draw* imports were not reached in this 360-frame replay. It does not establish that `0x00852760` is unreachable in other UI states. It also does not prove that descendants of `0x00852760` can or cannot submit a draw. The probe used the v659 manifest and v661 game data with the same runtime binary used for the v751/v752 callback provenance replays.

See the [machine-readable trace summary](process1_ui_gate_nested_draw_candidate_v753.json). Dispatch totals and frame counts are context only; this run does not prove frontend readiness or gameplay.
