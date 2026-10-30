# Process 1 state-block adapter frontier trace — v757

## Run identity and result

This is a controlled run of the original SHIFT retail PE32 inside the Linux
P-code guest runtime, not a native Windows or Wine launch.

- PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `0a310cf6be5b4934d021cdf56cbc8f2cd6e5b66278700708c29935076117124c`
- Module manifest: `module-manifest-v659-005a0ef0.json`, SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Game data: `pcode-game-data-v661`
- Trace log SHA-256: `cbf8c7325f570d3f5b4adead91f079ac04c1443dc1e3e9489babeba4f96ff2f9`

The probe completed 360 host frames with no blocker and zero validation errors.
The full, untruncated guest-call trace selected adapter methods
`0x0084FBC0` (BeginStateBlock), `0x0084FBF0` (EndStateBlock), and
`0x0084FD60`, plus D3D9 BeginStateBlock, EndStateBlock, and
DrawIndexedPrimitive imports. It recorded zero events. The bridge submitted
360 clears and 360 presents, with `guest_draw_translation=false`.

The main-thread PC at the probe stop was `0x0084E710`, with call stack
`0x0090488A → 0x009046AA → 0x00A69160 → 0x0040BA50 → 0x0054BE00 → 0x0082F780 → 0x0082DC20 → 0x0084E710`.
This differs from the v756 stop PC and is recorded as run context, not a
readiness signal. Dispatch counts are context only.

## Interpretation and limits

No Begin/EndStateBlock adapter method, `0x0084FD60` forwarder, or selected
D3D9 draw import was observed in this replay. This says only that these paths
were not reached during this 360-frame interval. It does not prove
unreachability in other UI states, establish the value or writers of
`BYTE[adapter+4]`, or prove retail rendering, frontend readiness, or race
entry. No guest state was forced to trigger the paths.

See the [machine-readable replay record](process1_stateblock_adapter_v757.json)
and the [static `0x0084F000` helper analysis](process1_adapter_state_sync_0084f000.md).
