# Retail no-draw and UI-gate frontier: v747–v750

**Date:** 2026-10-22. **Scope:** original retail SHIFT.exe through the P-code runtime. This records runtime evidence only; it does not establish a completed game launch or race.

## Pinned inputs and runtime

- Retail PE32 x86, PC retail 1.02, image base `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Runtime executable SHA-256 `dc66d4b3f7d6a10ca101d71fb1e1e7503653757e3b4606bf7e65bdb88bc023f7`.
- Runs v747–v750 used the DXT3 capture integration snapshot at P2 commit `f4147f33`. The P1 sources `recompiled_pcode_module.cpp` and `shift_runtime.cpp` match the PR #2140 branch byte-for-byte; `recompiled_pcode_module.cpp` SHA-256 is `914ef04f89d19fb51f0231c9589a17e8ee202602015374cb74a1bcde6ecd082a` in both trees. No renderer source was changed for these probes.
- Full retail logs are retained outside the repository under `/tmp/process1-retail-runtime-evidence/`; the hashes below pin each log. Packet-capture directories were empty.

## Probe results

| Run | Window / probes | Verified result | Retail log SHA-256 |
| --- | --- | --- | --- |
| v747 | 360 frames; `DrawIndexedPrimitive` import trace, stack slots ESP+0 through ESP+0x1c | `host-frame-loop`, exit 0, validation errors 0, 4,728 unique functions. Import trace enabled and not truncated; no DIP events. 360 clears and 360 presents were submitted. `guest_draw_translation=false`; this field is a diagnostic literal, not proof of whether an import entry was attempted. | `d434d8ad68f3cef44b78c4e33e5a91b73d7643fe348e5a00c685d13ce756d234` |
| v748 | 120 frames; all four D3D9 Draw/DrawUP imports; UI-state gate trace | All four draw imports were selected; trace was not truncated and contained no draw events. The gate ran 584 times. Every observed gate call saw the zero state/callback path and returned zero. Capture directory empty. | `61124cf3fc3c614d6ae6e5ca10fff1f85fb58e7b02b85d4f70eccecbd1b5e06e` |
| v749 | 120 frames; same draw/gate traces plus provenance for `0x00BE2534` | 584 gate calls read zero. Their last-writer provenance consistently identified `0x0062FDE0`, with ECX `0x00BE2510`, storing zero to `0x00BE2534`. The caller chain included `0x0062FFD0 -> 0x004E8BC0 -> 0x0050CF10`; no later write appeared in the window. No draw-import events; capture directory empty. | `db2322f373af01e24625680534a1bbb0903d0348f73b95853b8f3d93d1b9edf6` |
| v750 | 120 frames; same traces plus Win32, DirectInput and XInput imports; Up key press/release sent to guest window `0x01000000` | 584 gate calls still saw zero; all four draw-import traces had no events and were not truncated. The key messages reached WndProc `0x0040D040`, which called `DefWindowProcW` for WM_KEYDOWN (`0x0100`, VK_UP `0x26`) and WM_KEYUP (`0x0101`, VK_UP `0x26`). Counts: 586 `PeekMessageW`, two each `GetMessageW`, `TranslateMessage`, `DispatchMessageW`, and `DefWindowProcW`. Selected `DirectInput8Create`, XInput ordinals #2/#3/#5, `GetCursorPos`, and `SetCursorPos` imports were not called in this window. | `0017fcddc1c7b9a38a7ab7e2e690f247aac0c0d158aeb97c3b4df0135d4467c1` |

## Evidence interpretation

The runtime reached the host frame loop and executed clear/present work, but these observations do not demonstrate a guest D3D9 draw, frontend readiness, or gameplay. Dispatch totals are telemetry only. In particular, v747 reported fewer dispatches than v743 (1,722,972 versus 1,736,004); both ran 360 frames with 4,728 unique functions and zero validation errors, so this counter difference alone is not a regression signal.

Static inspection of retail `0x0082F3C0` shows it returns whether `[ECX+0x24] == 0`. `0x0050CEB0` checks that result and, on the observed path, returns zero when the state/callback conditions are absent. The confirmed writer `0x0062FDE0` initializes `[this+0x24]` and `[this+0x28]` to zero after its allocation/setup call. Its neighboring removal path decrements these fields. This is consistent with a collection count, but the exact collection/type role is not established by this evidence. Do not force the field or label it as a readiness switch.

The input probe establishes delivery through the Win32 message queue and the game's WndProc default path for Up. It does not establish that all keyboard/mouse input is unused. The selected DirectInput/XInput/cursor imports were simply not observed in this bounded window.

Process 2's report `process-reports/2026-10-22-process2-v743-no-draw-frontier.md` confirms that the checked P1-to-P2 wiring has one typed `DrawIndexedPrimitive` handler and no tested route that bypasses its import/adapter callback. The present trace therefore places the observed frontier before that P2 draw ingress. An unknown hook or untraced guest route is not ruled out.

## Next evidence target

Resolve the exact owner/type of `[0x00BE2510+0x24]` and identify its retail insertion/publication path. Instrument the proven writer and that single insertion point in one run, recording value, caller/return address, thread, and sequence. This distinguishes a correctly empty retail collection from a missing guest operation without changing original state.
