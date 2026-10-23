# Process 1 DrawIndexedPrimitive forwarder trace — v755

Date: 2026-10-22

## Run identity and result

This was a controlled replay of the original SHIFT retail PE32 inside the Linux P-code guest runtime, not a native Windows or Wine launch.

- PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`
- Module manifest: `module-manifest-v659-005a0ef0.json`, SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Game data: `pcode-game-data-v661`
- Trace log SHA-256: `a1511eff968080c79ef35960c5c387332d3c906b573a203ae566e083624e989a`

The replay completed 360 host frames with no reported blocker and zero validation errors. The guest call trace was enabled and not truncated. It selected adapter target `0x0084FD60` and the four D3D9 Draw/DrawUP imports. The trace contained zero events. The bridge reported 360 clear and 360 present submissions, with `guest_draw_translation=false`.

## Interpretation and limits

This is a bounded negative observation: the selected adapter and Draw* targets were not reached in this 360-frame replay. It does not establish that the retail path is unreachable in another UI state. The original PE's conditional static route through `0x0084FD60` remains proven by the separate [retail static analysis](process1_nested_draw_static_00852760.md); v755 does not establish execution of that route or a translated Vulkan draw.

Dispatch and frame totals are run context only. They do not prove game launch, frontend readiness, retail drawing, or gameplay. See the [machine-readable trace](process1_drawindexed_forwarder_v755.json).
