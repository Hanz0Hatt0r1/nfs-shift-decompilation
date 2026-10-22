# Process 1 retail message-loop frontier: v741–v746

Date: 2026-10-22  
Retail binary: SHIFT.exe PC 1.02, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Change under review

The Process 1 runtime now resolves the original retail message-loop imports `GetMessageW`, `TranslateMessage`, `DispatchMessageW`, and the observed `DefWindowProcW` keyboard branches. `GetMessageW` parks the guest coroutine while its thread-owned queue is empty, and posting a matching window message wakes that guest thread. The regression exercises the real guest entry point through the wait, post, wake, and completion sequence.

`DefWindowProcW` currently models only the observed `WM_KEYDOWN`, `WM_KEYUP`, and `WM_CHAR` messages, returning a zero `LRESULT` and applying four-argument x86 stdcall cleanup. Other messages remain explicit unsupported cases rather than silently receiving a guessed result.

## Retail evidence

All runs used the pinned retail PE, the v659 module manifest, game data v661, and an isolated integration build containing capture-backend revision `f4147f33`. Only Process 1 runtime/test files were copied into that integration build; no renderer source was edited in the Process 1 worktree.

| Probe | Guest input / frontier | Result |
| --- | --- | --- |
| v741 | XCB Up key; `WM_KEYDOWN (0x0100, VK_UP=0x26)` reached WndProc `0x0040D040` and called `DefWindowProcW` | Blocked on previously missing `USER32.dll!DefWindowProcW`; 462,261 dispatches. |
| v742 | Same Up key after adding the default keyboard branch | Passed through keydown, then blocked on `WM_KEYUP (0x0101)`; the retail frontier advanced. |
| v743 | Up press/release after keydown and keyup support | Reached `host-frame-loop`: 360 host frames; guest main thread was at `0x0082FAF0`; CreateDevice returned `S_OK`; the bridge submitted 360 clears and 360 presents. It recorded 1,129 clear requests and 1,127 present requests, with `guest_draw_translation=false`. |
| v744 | No injected input; traced `DINPUT8.dll!DirectInput8Create` | Reached a 10-frame host loop. No `DirectInput8Create` call appeared in the trace. This only says the API was not called on this startup path. |
| v745 | Enter key, before `WM_CHAR` support | `TranslateMessage` generated `WM_CHAR (0x0102)`; probe blocked on that exact `DefWindowProcW` message. |
| v746 | Enter key after `WM_CHAR` support | Reached `host-frame-loop`: 30 frames; guest main thread was at `0x0082F710`, statically identified as `CRenderer::BeginFrame`; bridge submitted 30 clears and 30 presents, with `guest_draw_translation=false`. |

Win32 documents say `TranslateMessage` places a `WM_CHAR` message on the queue for a translated key, and list Enter among keys that generate character messages. The original retail probe confirmed the exact `WM_CHAR` blocker and then passed it after support was added. See [WM_CHAR](https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-char) and [Using Keyboard Input](https://learn.microsoft.com/en-us/windows/win32/inputdev/using-keyboard-input).

## Verification

Built `shift_runtime_recompiled_pcode_module_check` and `shift_runtime` in the Process 1 worktree. The focused CTest passed after each `DefWindowProcW` branch was added:

```text
/usr/bin/ctest --test-dir native_runtime/build -R '^shift_runtime_recompiled_pcode_module$' --output-on-failure
1/1 Test #139: shift_runtime_recompiled_pcode_module ... Passed
```

The same focused test passed in the temporary capture-backend integration build before each retail probe. `git diff --check` passed in the Process 1 worktree.

## Limits and next frontier

The retail executable now runs its host frame loop after keyboard messages, and the last observed main-thread function is `CRenderer::BeginFrame`. The current integration still has no translated retail draw packet: `guest_draw_translation=false`, and `retail_rendering_proven=false`. Clear/Present submissions and interpreter dispatch totals do not establish a visible menu or a race.

The v744 DirectInput trace does not establish whether the game uses DirectInput later. The D3D9 packet handoff / zero-draw boundary has been sent to Process 2 for a separate renderer investigation. Process 1 should continue tracing original front-end input and the next guest runtime blocker without treating host-frame progress as game readiness.
