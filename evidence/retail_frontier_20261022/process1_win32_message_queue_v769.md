# Process 1 — Win32 guest message queue and keyboard delivery, v769–v772

## Scope

This change addresses the retail frontend message-pump boundary in the Linux
runtime. It wires host XCB key events into the synthetic guest Win32 window,
implements the imported `PeekMessageW`, `GetMessageW`, `TranslateMessage`, and
`DispatchMessageW` queue behavior, and invokes the guest window procedure. It
does not change D3D9-to-Vulkan renderer code.

## Retail evidence motivating the change

The source binary is PC retail SHIFT 1.02, PE32 x86, SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
The v768 retail trace identified `FUN_00633D40` as a message-pump loop: it calls
`PeekMessageW` with `PM_NOREMOVE`; if a message is present it calls
`GetMessageW`, `TranslateMessage`, and `DispatchMessageW`. The `WNDCLASSEXW`
registered by caller `0x006349F0` supplies guest WndProc `0x00634870`, and the
same startup path creates the synthetic guest window.

Before this change the compatibility implementation discarded the registered
WndProc, returned a synthetic HWND without retaining a queue, and always
returned zero from `PeekMessageW`. Retail evidence v768 recorded one
`RegisterClassExW`, one `CreateWindowExW`, one `ShowWindow`, and 1,122 empty
`PeekMessageW` results; no message translation or dispatch was observed.

## Implementation

- Retain the WndProc and creating guest thread when registering/creating the
  synthetic window.
- Queue host key-down/key-up events as guest `MSG` records with virtual key,
  scan code, transition/repeat bits, timestamp, and client coordinates.
- Match `PeekMessageW` / `GetMessageW` by HWND, thread, and message range;
  preserve `PM_NOREMOVE`, remove only for `PM_REMOVE`, and keep the caller's
  `MSG` untouched when `PeekMessageW` finds no event.
- Translate supported US-layout letters, digits, Backspace, Tab, Return,
  Escape, and Space to `WM_CHAR` records.
- Dispatch the registered guest WndProc through the existing guest x86
  dispatcher and provide a small `DefWindowProcW` fallback for the synthetic
  window.

The implementation remains in the guest ABI layer and does not depend on the
host pointer size. The XCB-to-virtual-key table currently covers the common
US keyboard keys used by the frontend. `GetMessageW` fails closed if invoked
with an empty queue; the observed retail caller reaches it only after a
successful `PeekMessageW`.

## Verification

- Built `shift_runtime_recompiled_pcode_module_check` and `shift_runtime` with
  CMake successfully.
- `/usr/bin/ctest --test-dir native_runtime/build -R
  '^shift_runtime_recompiled_pcode_module$' --output-on-failure` passed. The
  targeted fixture checks WndProc registration, synthetic window creation and
  visibility, posted key-down/key-up records, `PM_NOREMOVE`, removal by
  `GetMessageW`, `WM_CHAR` translation, guest WndProc dispatch, filtering, and
  preservation of `MSG` on an empty queue.
- Bounded v769 run executed the retail PE through the Linux runtime for 360
  host frames and exited 0 with zero validation errors. Runtime SHA-256:
  `7ad0319870c03ac2e0aa096ba5cdc5767c9843b58371a8477c2afaccbaf32678`.
  Trace log SHA-256:
  `e23028238e9ec2a09eff84d1ada7b36b7ccf59021e9dcae1b35eaf782ae54891`.
  It observed the class/window/show calls and 1,121 empty `PeekMessageW`
  returns. This no-input run did not observe a retail message.
- A v771 live-input run sent X11 key A and saw the full message-pump path, but
  its 1,200 frame request hit the 120 second bound before a final summary. A
  shorter v772 run then sent X11 key A to the mapped runtime window after the
  retail queue loop began and completed 360 host frames with exit 0 and zero
  validation errors. The selected WndProc `0x00634870` received exactly these
  messages in the trace: `WM_KEYDOWN` (`wParam=0x41`, `lParam=0x001e0001`),
  `WM_KEYUP` (`wParam=0x41`, `lParam=0xc01e0001`), and `WM_CHAR`
  (`wParam=0x61`, `lParam=0x001e0001`). Each returned zero and guest dispatch
  advanced through the callback. `PeekMessageW`/`GetMessageW` returned success
  for the queued input and `TranslateMessage` returned success for the
  character. This proves host-to-retail-WndProc keyboard delivery. The trace
  selected `DINPUT8.dll!DirectInput8Create`, `GetAsyncKeyState`,
  `GetKeyboardState`, and `GetRawInputData`, but recorded no invocation of
  these imports in this bounded run. v772 did not prove menu advancement, a
  retail draw, or gameplay. Trace log SHA-256:
  `fe55422568366dd7005e1994d9c271ec9617abe90b090eead95e23ab7d778ff3`.
  The 1,749,992 dispatches and 4,729 unique functions in the completed v769
  run are execution counters only.

## Remaining limits

Character translation covers only the listed US-layout keys.
`DefWindowProcW` is intentionally minimal. Retail menu advancement and
progression to a race remain unproven, and no renderer conclusion follows from
this work.
