from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_xcb_window_has_explicit_lifecycle_and_borrowed_native_handles():
    header = _text("native_vulkan/include/shift_xcb_window.h")
    source = _text("native_vulkan/src/xcb_vulkan_surface_probe.cpp")

    assert "typedef struct ShiftXcbWindow ShiftXcbWindow" in header
    assert "shift_xcb_window_create" in header
    assert "shift_xcb_window_destroy" in header
    assert "shift_xcb_window_poll" in header
    assert "Borrowed native handles" in header
    assert "shift_xcb_window_connection" in header
    assert "shift_xcb_window_id" in header

    assert "xcb_connect" in source
    assert "xcb_create_window_checked" in source
    assert "xcb_map_window_checked" in source
    assert "xcb_destroy_window" in source
    assert "xcb_disconnect" in source
    assert "xcb_connection_has_error" in source


def test_xcb_input_translation_matches_current_linux_runtime_controls():
    header = _text("native_vulkan/include/shift_platform_input.h")
    source = _text("native_vulkan/src/xcb_vulkan_surface_probe.cpp")

    for field in (
        "quit",
        "throttle",
        "brake",
        "steer_left",
        "steer_right",
    ):
        assert field in header

    # Preserve the existing shift_runtime.cpp XCB mappings exactly while moving
    # ownership/event translation behind the platform boundary.
    for keycode in ("case 9:", "case 24:"):
        assert keycode in source
    for keycode in ("case 111:", "case 25:"):
        assert keycode in source
    for keycode in ("case 116:", "case 39:"):
        assert keycode in source
    for keycode in ("case 113:", "case 38:"):
        assert keycode in source
    for keycode in ("case 114:", "case 40:"):
        assert keycode in source

    assert "XCB_DESTROY_NOTIFY" in source
    assert "input->quit = 1u" in source
    assert "input->throttle = pressed" in source
    assert "input->brake = pressed" in source
    assert "input->steer_left = pressed" in source
    assert "input->steer_right = pressed" in source
