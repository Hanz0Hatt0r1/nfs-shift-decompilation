# Process 1 — synchronous Win32 window lifecycle, v775

## Scope

This update makes the synthetic guest window deliver its creation and initial
visibility messages to the original retail window procedure. It changes only
the Win32 guest compatibility layer; it does not modify renderer code.

`CreateWindowExW` now prepares guest `CREATESTRUCTW` and
`NCCALCSIZE_PARAMS`/`WINDOWPOS` structures and synchronously invokes the
registered procedure with `WM_NCCREATE`, `WM_NCCALCSIZE`, and `WM_CREATE`.
It rejects window creation when the procedure rejects `WM_NCCREATE` or
`WM_CREATE`. `ShowWindow` sends `WM_SHOWWINDOW` when visibility changes and,
when showing, sends `WM_SIZE` and `WM_MOVE` with the stored client dimensions
and position. A creation request with `WS_VISIBLE` enters the visible state
and sends the same visibility messages after its creation messages.

Microsoft documents that creation messages reach the procedure before the
window is displayed, with some additional messages depending on class and
style: [About Windows](https://learn.microsoft.com/en-us/windows/win32/winmsg/about-windows).
The original retail trace below confirms the messages and parameters observed
for SHIFT's own window.

## Regression and build

- Built `shift_runtime_recompiled_pcode_module_check` and `shift_runtime`.
- `/usr/bin/ctest --test-dir native_runtime/build -R
  '^shift_runtime_recompiled_pcode_module$' --output-on-failure` passed.
- The fixture creates and shows a guest window with `DefWindowProcW`, then
  uses `FindWindowW` as a procedure that returns zero for `WM_NCCREATE`; the
  second `CreateWindowExW` call correctly returns `NULL`.
- The message-pump fixture creates its window with `WS_VISIBLE`, queues a key
  event before any `ShowWindow` call, and confirms the first `ShowWindow`
  reports that the window was already visible.

## Original retail run

- PE: SHIFT PC retail 1.02, PE32 x86, SHA-256
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Probe: v775, 120 requested frames, validation enabled, using the verified
  v659 module manifest to supply the already-built `rvi_005f1820` supplement.
- Result: `host-frame-loop`, exit 0, 120 frames, zero validation errors.
- Trace selected retail WndProc `0x00634870` and
  `USER32.dll!DefWindowProcW`; it was not truncated. The retail procedure
  received:
  - `WM_NCCREATE` (`0x81`), `wParam=0`, `lParam=0x10476e80`; returned `1`.
  - `WM_NCCALCSIZE` (`0x83`), `wParam=1`, `lParam=0x10476ee0`; returned `0`.
  - `WM_CREATE` (`0x01`), `wParam=0`, `lParam=0x10476e80`; returned `0`.
  - `WM_SHOWWINDOW` (`0x18`), `wParam=1`; returned `0`.
  - `WM_SIZE` (`0x05`), `wParam=SIZE_RESTORED`, packed size `0x02d00500`
    (1280 by 720); returned `0`.
  - `WM_MOVE` (`0x03`), packed position `0`; returned `0`.
- Runtime SHA-256: `4d5e118b93567f9e31f076edcb5c1e1d97f3543222d703d2b26fca8056346ee8`.
- Trace log SHA-256: `a86e8f06deefa5b9007188ed1db8424a0d91c2714ae3163de6237c948b02078b`.
- The run reported `retail_rendering_proven=false` and
  `guest_draw_translation=false`. Dispatch totals are context only; this run
  does not prove menu advancement, a retail draw, or reaching a race.

## Remaining compatibility limits

The shim sends the observed creation and visibility messages, but it does not
yet synthesize the full Windows window-position sequence or every
class/style-dependent creation message (including `WM_GETMINMAXINFO`,
`WM_WINDOWPOSCHANGING`, and `WM_WINDOWPOSCHANGED`). The synthetic window still
models one guest HWND. The successful bounded startup confirms the observed
messages are accepted by the retail procedure; it does not establish complete
Win32 window-manager compatibility.
