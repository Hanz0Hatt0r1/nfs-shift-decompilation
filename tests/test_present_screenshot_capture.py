from pathlib import Path

from tools.ppm_to_snapshot_svg import ppm_to_svg, read_ppm


def test_ppm_reader_and_svg_snapshot_are_deterministic(tmp_path):
    ppm = tmp_path / "frame.ppm"
    ppm.write_bytes(
        b"P6\n4 2\n255\n"
        + bytes([
            255, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255,
            0, 0, 255, 0, 0, 255, 255, 255, 255, 255, 255, 255,
        ])
    )

    width, height, payload = read_ppm(ppm)
    assert (width, height) == (4, 2)
    assert len(payload) == 24

    svg = ppm_to_svg(ppm, max_width=4, max_height=2, levels=2)
    assert 'viewBox="0 0 4 2"' in svg
    assert 'shape-rendering="crispEdges"' in svg
    assert "#ff0000" in svg
    assert "#00ff00" in svg
    assert "#0000ff" in svg
    assert "#ffffff" in svg


def test_present_capture_hook_is_opt_in_and_frame_cadenced(tmp_path):
    # The test fixture is intentionally source-oriented: Windows compilation
    # remains the authoritative validation for the native proxy.
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")
    assert 'SHIFT_D3D9_CAPTURE_SCREENSHOT' in source
    assert 'SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY' in source
    assert 'SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR' in source
    assert 'present_screenshot' in source
    assert 'write_backbuffer_ppm' in source


def test_d3d9_proxy_reports_startup_path():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")
    assert 'proxy_direct3dcreate9' in source
    assert 'proxy_system_d3d9_load_failed' in source
    assert 'proxy_system_d3d9_ready' in source
    assert 'g_proxy_entry_reported.compare_exchange_strong' in source


def test_runtime_trace_accepts_present_screenshot_events():
    from d3d9_runtime_trace import build_runtime_binding_evidence

    report = build_runtime_binding_evidence([
        {
            "event": "present_screenshot",
            "frame": 12,
            "event_index": 0,
            "path": "capture/shift_d3d9_frame_12.ppm",
        },
        {
            "event": "present_screenshot_failed",
            "frame": 13,
            "event_index": 1,
            "reason": "get-render-target-data-failed",
        },
    ])
    assert report["trace"]["frame_count"] == 2
    assert report["frames"][0]["screenshot_events"] == [{
        "event": "present_screenshot",
        "path": "capture/shift_d3d9_frame_12.ppm",
        "reason": None,
        "line": None,
    }]
    assert report["frames"][1]["screenshot_events"][0]["event"] == "present_screenshot_failed"



def test_mingw_d3d9_proxy_static_runtime_linking():
    cmake = Path("native_capture/CMakeLists.txt").read_text(encoding="utf-8")
    assert '-static' in cmake
    assert '-static-libgcc' in cmake
    assert '-static-libstdc++' in cmake


def test_linux_mingw_toolchain_targets_32bit_windows():
    toolchain = Path("native_capture/toolchains/mingw-i686.cmake").read_text(encoding="utf-8")
    assert "set(CMAKE_SYSTEM_NAME Windows)" in toolchain
    assert "set(CMAKE_SYSTEM_PROCESSOR x86)" in toolchain
    assert "i686-w64-mingw32-g++" in toolchain
