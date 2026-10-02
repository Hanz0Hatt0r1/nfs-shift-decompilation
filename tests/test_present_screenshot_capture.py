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
    assert 'WINEDLLOVERRIDES="$filtered_overrides;d3d9=n,b;d3dx9_41=n"' in wine
    assert 'WINEDLLOVERRIDES="d3d9=n,b;d3dx9_41=n"' in wine
    assert '[[ ! -s "$capture_path" ]]' in wine
    assert 'capture trigger did not fire' in wine
    assert 'resource trigger not observed: $resource_trigger' in wine
    assert 'exit 4' in wine



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
    assert "TriggerCapture/ResourceTrigger cannot be combined with FrameStart/FrameEnd" in powershell

    assert "--trigger" in wine
    assert "--pre-frames" in wine
    assert "--post-frames" in wine
    assert "capture.trigger" in wine
    assert "SHIFT_D3D9_CAPTURE_TRIGGER_FILE" in wine
    assert "SHIFT_D3D9_CAPTURE_TRIGGER_KEY=0x79" in wine
    assert "--trigger/--resource-trigger cannot be combined with --frame-start/--frame-end" in wine


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
        'surface_signature("rt"',
        'surface_signature("depth"',
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
    assert "resource_trigger_already_fired(signature)" in source
    assert "mark_resource_trigger_fired(signature)" in source
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT" in source
    assert "table[object] = signature" in source


def test_resource_trigger_launchers_accept_signature_rules():
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert '[string]$ResourceTrigger = ""' in powershell
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER" in powershell
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT" in powershell
    assert "[switch]$ResourceTriggerRepeat" in powershell
    assert "TriggerCapture/ResourceTrigger cannot be combined" in powershell

    assert "--resource-trigger" in wine
    assert "--resource-trigger-repeat" in wine
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER" in wine
    assert "SHIFT_D3D9_CAPTURE_RESOURCE_TRIGGER_REPEAT" in wine
    assert "--trigger/--resource-trigger cannot be combined" in wine


def test_signature_discovery_suppresses_full_render_stream():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "SHIFT_D3D9_CAPTURE_SIGNATURE_DISCOVERY" in source
    assert 'writer().write_event("resource_signature_use"' in source
    assert "(count & (count - 1)) != 0" in source
    assert "if (signature_discovery_enabled()) return;" in source
    assert "record_resource_signature_use(bind_event, signature, object)" in source
    assert "if (!signature_discovery_enabled()) patch_vertex_buffer_object" in source
    assert "if (!signature_discovery_enabled()) patch_index_buffer_object" in source
    assert "if (!signature_discovery_enabled()) patch_texture_object" in source
    assert "if (!signature_discovery_enabled()) patch_cube_texture_object" in source
    assert "lifecycle_render_patches" in source
    assert "case SLOT_CREATE_PIXEL_SHADER:" in source
    assert "case SLOT_SET_PIXEL_SHADER:" in source
    assert "case SLOT_DRAW_INDEXED_PRIMITIVE:" not in source[source.index("if (signature_discovery_enabled())", source.index("void patch_device")):source.index("} else {", source.index("if (signature_discovery_enabled())", source.index("void patch_device")))]

    assert "[switch]$SignatureDiscovery" in powershell
    assert "SHIFT_D3D9_CAPTURE_SIGNATURE_DISCOVERY" in powershell
    assert "SignatureDiscovery cannot be combined with frame or trigger capture" in powershell

    assert "--signature-discovery" in wine
    assert "SHIFT_D3D9_CAPTURE_SIGNATURE_DISCOVERY" in wine
    assert "--signature-discovery cannot be combined with frame or trigger capture" in wine
    assert "resource_signatures.json" in wine


def test_wine_launcher_forces_native_d3dx9_41_preference():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    # SHIFT's D3DX effect/technique path is unstable with Wine's builtin
    # implementation. Prefer the native runtime when it is present, while
    # retaining builtin fallback through the n,b override.
    assert 'd3dx9_41=n' in wine
    assert '"${name,,}" == "d3dx9_41"' in wine


def test_capture_launchers_clear_previous_session_outputs():
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'rm -f "$capture_path" "$crash_path"' in wine
    assert '"$output/resource_signatures.json"' in wine
    assert '"$output/capture.trigger"' in wine

    assert 'Remove-Item -LiteralPath $capturePath -Force' in powershell
    assert 'Remove-Item -LiteralPath $crashPath -Force' in powershell
    assert 'Join-Path $out "resource_signatures.json"' in powershell
    assert 'Join-Path $out "capture.trigger"' in powershell


def test_capture_launchers_accept_explicit_d3dx9_41_source_path():
    powershell = Path("tools/run_shift_capture.ps1").read_text(encoding="utf-8")
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "--d3dx9-41" in wine
    assert 'wine_prefix="${game%%/drive_c/*}"' in wine
    assert 'drive_c/windows/syswow64/d3dx9_41.dll' in wine
    assert 'drive_c/windows/system32/d3dx9_41.dll' in wine
    assert 'backup_d3dx="$output/original_d3dx9_41.dll"' in wine
    assert 'cp -f "$d3dx9_41" "$target_d3dx"' in wine
    assert 'cp -f "$backup_d3dx" "$target_d3dx"' in wine
    assert 'd3dx_same_file=1' in wine

    assert '[string]$D3DX9_41 = ""' in powershell
    assert '$targetD3DX = Join-Path $gameDir "d3dx9_41.dll"' in powershell
    assert '$backupD3DX = Join-Path $out "original_d3dx9_41.dll"' in powershell
    assert 'Copy-Item -LiteralPath $d3dxPath -Destination $targetD3DX -Force' in powershell
    assert 'Copy-Item -LiteralPath $backupD3DX -Destination $targetD3DX -Force' in powershell
    assert 'D3DX9_41 must point to an external source DLL' in powershell


def test_wine_d3dx9_41_is_staged_into_prefix_and_forced_native_only():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'if [[ "$game" == */drive_c/* ]]' in wine
    assert 'wine_prefix="${game%%/drive_c/*}"' in wine
    assert 'drive_c/windows/syswow64/d3dx9_41.dll' in wine
    assert 'drive_c/windows/system32/d3dx9_41.dll' in wine
    assert 'WINEDLLOVERRIDES="$filtered_overrides;d3d9=n,b;d3dx9_41=n"' in wine
    assert 'D3DX9 sha256:' in wine


def test_wine_launcher_rejects_d3dx_architecture_mismatch():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "pe_machine()" in wine
    assert "pe_machine_name()" in wine
    assert 'game_machine="$(pe_machine "$game")"' in wine
    assert 'd3dx_machine="$(pe_machine "$d3dx9_41")"' in wine
    assert 'if [[ "$d3dx_machine" != "$game_machine" ]]' in wine
    assert "d3dx9_41.dll architecture mismatch:" in wine
    assert 'game_machine" == "0x014c"' in wine
    assert 'PE arch : game=' in wine


def test_wine_launcher_skips_copy_when_d3dx_source_is_prefix_target():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert '"$d3dx9_41" -ef "$target_d3dx"' in wine
    assert "d3dx_same_file=1" in wine
    assert "(( ! d3dx_same_file ))" in wine
    assert "if ((d3dx_mutated)); then" in wine
    assert "source already resolves to the Wine prefix DLL; no copy needed" in wine


def test_wine_launcher_exports_inferred_prefix_before_winepath_and_wine():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'export WINEPREFIX="$wine_prefix"' in wine
    assert wine.index('export WINEPREFIX="$wine_prefix"') < wine.index('capture_windows="$(to_wine_path "$capture_path")"')
    assert wine.index('export WINEPREFIX="$wine_prefix"') < wine.index('"$wine_command" "$game"')
    assert 'echo "WINEPREFIX: $WINEPREFIX"' in wine
    assert 'wine_resolved="$(command -v "$wine_command")"' in wine
    assert 'winepath_resolved="$(command -v "$winepath_command")"' in wine
    assert 'echo "Wine exe : $wine_resolved"' in wine
    assert 'echo "Winepath : $winepath_resolved"' in wine


def test_trigger_buffer_payloads_defer_disk_io_until_trigger():
    source = Path("native_capture/shift_d3d9_capture.cpp").read_text(encoding="utf-8")

    for token in (
        "struct DeferredBufferPayload",
        "g_deferred_buffer_payloads",
        "retain_or_write_buffer_payload",
        "flush_deferred_buffer_payloads_for_trigger",
        "discard_deferred_buffer_payload",
        "activate_capture_trigger",
        "writer().trigger_is_active()",
    ):
        assert token in source

    assert "DeferredBufferPayload{state, std::move(payload)}" in source
    assert "if (!activate_capture_trigger(g_frame.load())) return false;" in source
    assert "activate_capture_trigger(g_frame.load());" in source
    assert "write_buffer_payload_file(" in source
    assert "g_deferred_buffer_payloads.clear();" in source
    assert "discard_deferred_buffer_payload(*out_buffer);" in source


def test_wine_launcher_warns_on_portproton_prefix_with_external_wine():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'portproton_root="${wine_prefix%%/data/prefixes/*}"' in wine
    assert 'PW_WINE_USE' in wine
    assert 'wine_resolved="$(command -v "$wine_command")"' in wine
    assert 'PortProton prefix is being launched with Wine outside the PortProton tree' in wine
    assert 'use --wine with the Wine/Proton binary selected by PortProton' in wine


def test_wine_launcher_auto_selects_portproton_runtime_and_matching_winepath():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'wine_command_explicit=0' in wine
    assert '--wine) wine_command=' in wine
    assert 'wine_command_explicit=1' in wine
    assert 'portproton_wine_use=' in wine
    assert '$portproton_root/data/dist/$portproton_wine_use/bin/wine' in wine
    assert '$portproton_root/data/dist/$portproton_wine_use/files/bin/wine' in wine
    assert 'sibling_winepath="${wine_resolved%/*}/winepath"' in wine
    assert 'winepath_command="$sibling_winepath"' in wine
    assert 'capture_windows="$(to_wine_path "$capture_path")"' in wine
    assert 'Runtime : auto-selected from PW_WINE_USE=' in wine


def test_wine_launcher_parses_portproton_ppdb_without_sed_regex():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "ppdb_export_value()" in wine
    assert "shlex.split(raw, comments=True, posix=True)" in wine
    assert 'ppdb_export_value "$ppdb" PW_WINE_USE' in wine
    assert "sed -n 's/" not in wine


def test_wine_launcher_avoids_system_winepath_when_runtime_has_none():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "unix_to_wine_z_path()" in wine
    assert "to_wine_path()" in wine
    assert 'winepath_resolved="internal Z: path mapping"' in wine
    assert 'winepath_command="winepath"' not in wine
    assert 'capture_windows="$(to_wine_path "$capture_path")"' in wine
    assert 'crash_windows="$(to_wine_path "$crash_path")"' in wine
    assert 'SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR="$(to_wine_path "$buffer_dir")"' in wine
    assert 'avoiding external winepath/wineserver startup' in wine


def test_wine_launcher_rejects_stale_shift_capture_proxy_as_backend():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert "is_shift_capture_proxy()" in wine
    assert 'b"SHIFT_D3D9_CAPTURE_MODE"' in wine
    assert 'b"SHIFT_D3D9_CRASH_DIAGNOSTICS"' in wine
    assert 'b"proxy_d3d9_backend_selected"' in wine
    assert 'stale_target_proxy=1' in wine
    assert 'stale_sidecar_proxy=1' in wine
    assert 'stale_capture_d3d9.dll' in wine
    assert 'stale_capture_d3d9.shift_backend.dll' in wine
    assert 'if ((stale_sidecar_proxy)); then' in wine
    assert 'elif ((had_sidecar)); then' in wine
    assert 'archived old SHIFT capture proxy' in wine
    assert 'Backend : Wine/system d3d9.dll' in wine


def test_wine_launcher_uses_portproton_start_environment_for_portproton_prefixes():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'portproton_start="$portproton_root/data/scripts/start.sh"' in wine
    assert "use_portproton_start=1" in wine
    assert 'backup_ppdb="$output/original_SHIFT.exe.ppdb"' in wine
    assert 'cp -p "$ppdb" "$backup_ppdb"' in wine
    assert 'if ((ppdb_mutated)); then' in wine
    assert 'cp -p "$backup_ppdb" "$ppdb"' in wine
    assert "# SHIFT_CAPTURE_TEMP_BEGIN" in wine
    assert 'stream.write("export PW_GUI_DISABLED_CS=1\\n")' in wine
    assert 'name.startswith("SHIFT_D3D9_")' in wine
    assert 'shlex.quote(os.environ.get("WINEDLLOVERRIDES", ""))' in wine
    assert 'echo "Launcher: $portproton_start"' in wine
    assert 'bash "$portproton_start" "$game" "${game_args[@]}"' in wine


def test_portproton_capture_temporarily_disables_gamescope():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'stream.write("export PW_GAMESCOPE=0\\n")' in wine
    assert 'Gamescope: disabled for capture session' in wine
    assert 'cp -p "$backup_ppdb" "$ppdb"' in wine


def test_portproton_capture_enables_low_noise_loader_diagnostics():
    wine = Path("tools/run_shift_capture_wine.sh").read_text(encoding="utf-8")

    assert 'stream.write("export WINEDEBUG=err+all\\n")' in wine
    assert 'stream.write("export DXVK_LOG_LEVEL=info\\n")' in wine
    assert 'Diag    : WINEDEBUG=err+all; DXVK_LOG_LEVEL=info' in wine
    assert 'cp -p "$backup_ppdb" "$ppdb"' in wine
