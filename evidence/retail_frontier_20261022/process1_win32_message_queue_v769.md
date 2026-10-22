# Process 1 — Win32 guest message queue and keyboard delivery, v769

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
- A second bounded live-input run sent X11 key A to the mapped runtime window
  after the retail synthetic window was visible. In the v771 trace,
  `PeekMessageW` returned 1 three times, `GetMessageW` returned 1 three times,
  `TranslateMessage` returned 1 once, and `DispatchMessageW` returned 0 three
  times; guest dispatch advanced during those callbacks. This proves that a
  host key reached the retail guest message pump and WndProc path. The 1,200
  frame run hit its 120 second bound before a final frame-loop summary; it does
  not establish menu advancement, a retail draw, or gameplay. Trace log
  SHA-256: `24d1738f47785c65456f2ee830bbd8ea37ceed4b09f7df83c14a08d8606529fa`.
  The 1,749,992 dispatches and 4,729 unique functions in the completed v769
  run are execution counters only.

## Remaining limits

Character translation covers only the listed US-layout keys.
`DefWindowProcW` is intentionally minimal. Retail menu advancement and
progression to a race remain unproven, and no renderer conclusion follows from
this work.
