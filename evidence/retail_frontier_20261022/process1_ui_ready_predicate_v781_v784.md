# Process 1 — retail UI readiness predicate frontier, v781–v784

Date: 2026-10-22. These are controlled replays of the original retail PE32 inside the Linux P-code guest runtime, not a native Windows/Wine launch.

## Run identity

- Original PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256: `4d5e118b93567f9e31f076edcb5c1e1d97f3543222d703d2b26fca8056346ee8`
- Game data: `pcode-game-data-v661`
- Module manifest: `module-manifest-v659-005a0ef0.json`
- All runs completed their requested host-frame loops with zero Vulkan validation errors. None proves the retail menu, a race, or gameplay.

| Replay | Frames | Relevant evidence | Log SHA-256 | Summary JSON SHA-256 |
|---|---:|---|---|---|
| v779 | 360 | `0x0054BB20` and gate call trace; 1121 `0x0050CEB0` gate calls returned zero | `bf0cd510c201b58c6bbde5bf1038afab60bb5333a95fd7635789d066f206716c` | `17dc5aee2b9e9d7678a6654542b19dc3cd1db32f4d711aa46c9080c9fddbc426` |
| v781 | 360 | `0x0054BB20` state slots and provenance for `0x00BE2B38` | `a940d46d3134d3ee06cb9922ac9dd216a75dd7e285eeb33a1951510fa8c83416` | `9bb65b8835cf8351ce44c6ad771d561e72c17c0e559cb3e8e25c455289c6d461` |
| v782 | 360 | `0x00508EA0/90/C0` predicate results and object slots; call trace hit its 8192-event cap | `90b7227ea0b2b64298b0d9482dd1f4138b8cad4fb83faefd1a92a8acf497a8f1` | `86525705d2a9b5925860329f2f454e8e56426dc7eb93e786bd771b59864e3ed1` |
| v783 | 360 | byte `0x27DFA629` last-writer provenance; call trace hit its 8192-event cap | `60030bf09db2461ca7be04fa8c492febb6dbcec5e6eefda1259f1a4e560b6797` | `c255ffb9f441158439054cd41685b333fb3df9210f58da8e9c1322f368878abd` |
| v784 | 120 | callees of `0x00508860`, readiness-reader returns and byte provenance | `3994676fc17cf5c70079c103eac0b29d9e36973c2d79be797969c7227645c8cf` | `1c4af3c69524e47a000a965e7fed0e641c033c661ffb684cab88f0215a8cb2c0` |

## Observations

1. In v781, `0x0054BB20` was entered 1122 times. Its progress fields reached 30 (`[param+0x1EF8]`, with `[param+0x1EFC]` equal to 30.0f) and stayed there; `[param+0x1F04]` remained zero on every recorded entry. The phase transition in the original function therefore did not occur in this replay.
2. In v782/v783, the recorded calls from `0x0054BB20` to `0x00508EA0` and `0x00508E90` returned zero. In sampled object `ECX=0x27DFA5FC`, the state DWORD at `+0x28` was 1, the active byte at `+0x2C` was 1, and the readiness byte at `+0x2D` was 0. `0x00508EC0` was not called in the captured records because the earlier short-circuit predicate failed. v782/v783 traces were truncated at the configured event cap, so their counts are lower bounds.
3. v783 provenance identifies the last write to byte `0x27DFA629` (`ECX+0x2D`) as a one-byte zero store by `0x005092F0`, at dispatch 461058. The call came from `0x0054B8B0` (return address `0x0054BAC8`) on guest thread `0x00175C45`. In v784, the same recorded writer remained the last writer through the end of the replay.
4. The original instructions in `0x005092F0` explicitly clear `[EDI+0x2D]` after its `0x00554050` guard passes. The function then walks a linked list and calls `0x00508860` for each item. `0x00508860` stores its incoming EDX into the list item at `+0xE8`, makes one indirect call through that item's vtable slot `+0x4`, and on a zero return updates only that list item's `+0xE4` and `+0xEC` fields in its own instructions. It contains no direct store to the original owner's `+0x2D` byte.
5. In v784, 9 calls from `0x00508860` were recorded: six to `0x005AA830`, one each to `0x0054B510`, `0x0054AEA0`, and `0x0054AA10`. These observed indirect targets all returned zero. The separate `0x00508E90` getter ran 591 times and returned zero every time. Its trace still named `0x005092F0` as the last writer of `0x27DFA629`.
6. v781 also recorded byte `0x00BE2B38` as zero, last written by `0x0055E6B0` (one-byte store, dispatch 130594). In v779, `0x0054BB20` called `0x00508EA0` with zero returns and the UI state gate returned zero 1121 times. These are separate state observations; they do not establish why the guest has not enabled the readiness byte.

## Bounded conclusion and next evidence needed

The proven immediate blocker is that the original `0x0054BB20` first-phase predicate remains false because `0x00508E90` reads zero from the worker object's `+0x2D` byte. The confirmed last writer clears that byte during `0x005092F0`; the called list-item helper has no direct store to that owner byte. The v784 runtime trace shows no later write to the owner byte during that replay. The indirect list-item callbacks or another original path may still affect readiness in other circumstances; this evidence does not show an original-semantics bug or justify forcing the flag.

Next investigation should identify the original writer/event that can set the owner's `+0x2D` byte to one, bounded to the relevant callback/list lifecycle and with a complete original PE instruction block. Keep the worker flag and gate states unchanged until their producer is proven.
