from pathlib import Path
import subprocess

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



def test_d3d9_proxy_can_chainload_preserved_backend():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")
    assert 'SHIFT_D3D9_BACKEND' in source
    assert 'd3d9.shift_backend.dll' in source
    assert 'proxy_d3d9_backend_selected' in source
    assert 'backend-resolves-to-proxy' in source


def test_capture_launchers_preserve_backend_and_default_to_diagnostics():
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert '[string]$Mode = "Diagnostic"' in powershell
    assert 'd3d9.shift_backend.dll' in powershell
    assert 'SHIFT_D3D9_CAPTURE_MODE' in powershell
    assert 'SHIFT_D3D9_CRASH_LOG' in powershell
    assert 'SHIFT_D3D9_CRASH_DIAGNOSTICS' in powershell
    assert 'SHIFT_D3D9_CAPTURE_FRAME_START' in powershell
    assert 'SHIFT_D3D9_CAPTURE_FRAME_END' in powershell
    assert 'CaptureBufferPayloads' in powershell
    assert 'CaptureTexturePayloads' in powershell
    assert 'mode="diagnostic"' in wine
    assert 'd3d9.shift_backend.dll' in wine
    assert 'SHIFT_D3D9_CRASH_LOG' in wine
    assert 'SHIFT_D3D9_CRASH_DIAGNOSTICS' in wine
    assert 'SHIFT_D3D9_CAPTURE_FRAME_START' in wine
    assert 'SHIFT_D3D9_CAPTURE_FRAME_END' in wine
    assert '--frame-start' in wine
    assert '--frame-end' in wine
    assert '--buffer-payloads' in wine
    assert '--texture-payloads' in wine
    assert 'WINEDLLOVERRIDES="d3d9=n,b' in wine



def test_wine_capture_launcher_has_valid_bash_syntax():
    subprocess.run(
        ["bash", "-n", "tools/run_shift_capture_wine.sh"],
        check=True,
    )


def test_d3d9_capture_supports_bounded_replay_state_stream():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")

    assert 'SHIFT_D3D9_CAPTURE_FRAME_START' in source
    assert 'SHIFT_D3D9_CAPTURE_FRAME_END' in source
    assert 'capture_frame_active()' in source
    assert 'bounded_capture_enabled()' in source

    for event in (
        'set_render_target',
        'set_depth_stencil_surface',
        'set_viewport',
        'set_render_state',
        'set_texture_stage_state',
        'set_sampler_state',
        'set_scissor_rect',
        'begin_scene',
        'end_scene',
        'clear',
        'draw_primitive',
        'draw_indexed_primitive',
        'draw_primitive_up',
        'draw_indexed_primitive_up',
    ):
        assert (
            f'write_event("{event}"' in source
            or f'write_render_event("{event}"' in source
        )

    for slot in (
        'SLOT_SET_RENDER_TARGET',
        'SLOT_SET_DEPTH_STENCIL_SURFACE',
        'SLOT_SET_VIEWPORT',
        'SLOT_SET_RENDER_STATE',
        'SLOT_SET_TEXTURE_STAGE_STATE',
        'SLOT_SET_SAMPLER_STATE',
        'SLOT_SET_SCISSOR_RECT',
        'SLOT_DRAW_PRIMITIVE',
        'SLOT_DRAW_PRIMITIVE_UP',
        'SLOT_DRAW_INDEXED_PRIMITIVE_UP',
    ):
        assert slot in source


def test_bounded_capture_keeps_resource_creation_metadata_global():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")

    # Create events must stay outside capture_frame_active() gating so a
    # bounded frame can still resolve resources created earlier in the run.
    for function_name in (
        'hook_create_texture',
        'hook_create_cube_texture',
        'hook_create_vertex_buffer',
        'hook_create_index_buffer',
        'hook_create_vertex_declaration',
        'hook_create_vertex_shader',
        'hook_create_pixel_shader',
    ):
        start = source.index(f'HRESULT STDMETHODCALLTYPE {function_name}(')
        next_hook = source.find('\nHRESULT STDMETHODCALLTYPE ', start + 1)
        if next_hook < 0:
            next_hook = len(source)
        body = source[start:next_hook]
        assert 'capture_frame_active()' not in body


def test_trigger_capture_uses_hotkey_file_and_ring_buffer():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")

    for token in (
        "SHIFT_D3D9_CAPTURE_TRIGGER",
        "SHIFT_D3D9_CAPTURE_TRIGGER_PRE_FRAMES",
        "SHIFT_D3D9_CAPTURE_TRIGGER_POST_FRAMES",
        "SHIFT_D3D9_CAPTURE_TRIGGER_KEY",
        "SHIFT_D3D9_CAPTURE_TRIGGER_FILE",
        "GetAsyncKeyState",
        "VK_F10",
        "render_ring",
        "pending_metadata",
        "write_render_event",
        'make_line("capture_trigger"',
        'make_line("capture_trigger_complete"',
    ):
        assert token in source

    assert "trigger_pre_frames() + 1" in source
    assert "flush_lines.begin()" in source
    assert "a.sequence < b.sequence" in source
    assert "capture_trigger_requested()" in source
    assert "complete_trigger_after_present" in source


def test_trigger_capture_launchers_expose_scene_capture_controls():
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "[switch]$TriggerCapture" in powershell
    assert "[int]$PreFrames = 2" in powershell
    assert "[int]$PostFrames = 2" in powershell
    assert "SHIFT_D3D9_CAPTURE_TRIGGER_FILE" in powershell
    assert '"0x79"' in powershell
    assert "TriggerCapture cannot be combined with FrameStart/FrameEnd" in powershell

    assert "--trigger" in wine
    assert "--pre-frames" in wine
    assert "--post-frames" in wine
    assert "capture.trigger" in wine
    assert "SHIFT_D3D9_CAPTURE_TRIGGER_FILE" in wine
    assert "SHIFT_D3D9_CAPTURE_TRIGGER_KEY=0x79" in wine
    assert "--trigger cannot be combined with --frame-start/--frame-end" in wine


def test_resource_signature_trigger_is_stable_and_bind_driven():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")

    for token in (
        "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER",
        "resource_trigger_rules",
        "resource_trigger_matches",
        "resource_trigger_match",
        "content_fnv1a64",
        "fnv1a64_hex",
        '"vs:" + hash',
        '"ps:" + hash',
        '"decl:" + hash',
        '"vb:" + std::to_string(length)',
        '"ib:" << length',
        'texture_signature("tex"',
        '"cube", edge_length',
    ):
        assert token in source

    # Matching is intentionally performed on stable signatures at binding time,
    # not on per-run COM pointer values.
    for bind_event in (
        "set_texture",
        "set_vertex_shader",
        "set_pixel_shader",
        "set_vertex_declaration",
        "set_stream_source",
        "set_indices",
    ):
        assert f'maybe_trigger_for_resource("{bind_event}"' in source

    assert "resource_trigger_matches(signature)" in source
    assert "table[object] = signature" in source


def test_resource_trigger_launchers_accept_signature_rules():
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert '[string]$ResourceTrigger = ""' in powershell
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER" in powershell
    assert "TriggerCapture/ResourceTrigger cannot be combined" in powershell

    assert "--resource-trigger" in wine
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER" in wine
    assert "--trigger/--resource-trigger cannot be combined" in wine
