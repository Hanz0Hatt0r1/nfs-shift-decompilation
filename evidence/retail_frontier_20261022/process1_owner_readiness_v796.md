# Original-PE UI readiness trace, v796

## Run identity and limits

This was a bounded replay of the original Need for Speed SHIFT PC retail 1.02
PE32 x86 executable in the Linux P-code guest runtime, not a recompiled game
or native Windows/Wine launch.

- `SHIFT.exe` SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`
- Game data: `pcode-game-data-v661`
- Module manifest: `module-manifest-v659-005a0ef0.json`; SHA-256
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`
- Probe: 360 host frames, exit 0, 1,750,173 P-code dispatches, 4,733 unique
  functions, zero Vulkan validation errors.
- Frontier: status `host-frame-loop`; the saved main-thread function was
  `0x006472D0`. Four worker threads were waiting and two runnable at the final
  snapshot.
- Targeted guest-call trace: 1,125 events, not truncated. Targets were
  `0x005092F0`, `0x005093A0`, and `0x005088A0`; target slots sampled offsets
  `0x14`, `0x28`, `0x2D`, `0xAC`, `0xAD`, and `0x110`. Exact-address write
  provenance was enabled for `0x27DFA629`.
- Log SHA-256: `1b83f1b60c30882712a16150864cca513b8b0274acfdbdff01a3416a333c2441`.
- Summary JSON SHA-256: `bfb59049373da509f40193adff85b62b5d11e58915c411fd522205107b04eba9`.

The bridge reported `guest_draw_translation=false` and
`retail_rendering_proven=false`. This run does not prove a visible retail menu,
native game launch, or race entry. Counts and current-function snapshots are
execution diagnostics only.

## Bounded UI observations

The selected owner was `O=0x27DFA5FC`.

- `0x005092F0` ran once at dispatch 461057 with `ECX=O`, `EDX=0x00AC52C4`,
  and `DWORD[O+0x14]=9`. Its one-byte store at `O+0x2D` was recorded at
  dispatch 461058. The aligned containing word at `0x27DFA628` was
  `0x27DF0001`, whose byte at `0x27DFA629` (`O+0x2D`) is zero.
- `0x005093A0` ran 1,119 times from caller `0x0054BB20`, with `ECX=O` and
  `EDX=0x00AC52C4`. Every recorded return was EAX zero. At every sampled
  entry, the unaligned DWORD read from `O+0x2D` was `0x0027DF00`, so its low
  byte—the readiness byte—was zero. The last writer remained the one-byte
  zero store in `0x005092F0` at dispatch 461058; no later write to this exact
  address was recorded in this replay.
- `0x005088A0` ran five times and returned EAX 5 each time: once from
  `0x005092F0` at return EIP `0x00509370`, and four times from
  `0x005093A0` callsite `0x00509689` at return EIP `0x0050968E`.
- Relative to v795, the replay comparison reported `advanced`; the final main
  function moved from `0x007DA290` to `0x006472D0`. This does not establish
  that a UI phase gate opened or identify a cause for the readiness value.

## Bounded conclusion

The trace confirms that the original `0x005093A0` body repeatedly executes
against the same observed owner whose `+0x14` count is nine, and that its
selected `0x005088A0` queries return five. Nevertheless, `BYTE[O+0x2D]`
remains zero throughout the sampled entries and its last recorded writer stays
`0x005092F0`. This trace alone does not establish why the positive readiness
store in the original body is not reached, nor does it justify forcing that
byte or changing P-code semantics. See the [machine-readable summary](process1_owner_readiness_v796.json).
