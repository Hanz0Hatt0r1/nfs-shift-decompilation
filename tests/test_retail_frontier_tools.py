"""Regression tests for retail frontier automation and D3D9 comparison.

Runs without SHIFT.exe, retail data, a display, Vulkan, or a multi-GB P-code ELF.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import retail_frontier as frontier  # noqa: E402
import compare_shift_d3d9 as d3d9  # noqa: E402


class RetailFrontierTests(unittest.TestCase):
    def test_default_probe_mesh_is_a_minimal_mgeo(self):
        env = {}
        temporary = frontier._ensure_probe_mesh(env)
        self.assertIsNotNone(temporary)
        try:
            mesh = Path(env["SHIFT_ENTRYPOINT_PROBE_MESH"])
            blob = mesh.read_bytes()
            self.assertEqual(blob[:4], b"MGEO")
            self.assertEqual(len(blob), 82)
        finally:
            temporary.cleanup()

    def test_real_v173_diagnostic(self):
        log = ROOT / "evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log"
        result = frontier.inspect_log(log.read_text(encoding="utf-8"), 1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["dispatches"], 49065)
        self.assertEqual(result["unique_functions"], 1249)
        self.assertEqual(result["return_address"], "0x00839b53")
        self.assertIn("D3DXCreateTexture", result["blocker"])
        self.assertFalse(result["retail_rendering_proven"])

    def test_real_v193_remains_a_host_frame_loop(self):
        path = ROOT / "evidence/retail_frontier_20261019/entrypoint_probe_v193_automation.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["report"]["status"], "host-frame-loop")
        self.assertEqual(record["report"]["comparison"]["result"], "advanced")
        self.assertEqual(record["guest_present_requests"], 121)
        self.assertEqual(record["host_frames_rendered"], 120)
        self.assertEqual(record["validation_errors"], 0)
        self.assertFalse(record["present_vulkan_frame_transfer"])
        self.assertFalse(record["retail_rendering_proven"])

    def test_real_v194_queues_guest_clear_and_present(self):
        path = ROOT / "evidence/retail_frontier_20261019/entrypoint_probe_v194_automation.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        bridge = record["d3d9_vulkan_bridge"]
        self.assertEqual(record["status"], "host-frame-loop")
        self.assertEqual(record["frames_rendered"], 120)
        self.assertEqual(record["validation_errors"], 0)
        self.assertEqual(bridge["clear_requests"], 122)
        self.assertEqual(bridge["present_requests"], 121)
        self.assertEqual(bridge["clear_submissions"], 120)
        self.assertEqual(bridge["present_submissions"], 120)
        self.assertEqual(bridge["pending_presents"], 1)
        self.assertFalse(bridge["guest_draw_translation"])
        clear = record["d3d9_clear_request"]
        self.assertEqual(clear["flags"], "0x00000007")
        self.assertEqual(clear["color"], "0x00000000")
        self.assertEqual(clear["depth_bits"], "0x3f800000")
        self.assertEqual(record["guest_main_thread_function"], "0x006472d0")
        self.assertEqual(record["worker_waiting_count"], 4)
        self.assertEqual(len(record["probe_log_sha256"]), 64)
        self.assertFalse(record["retail_rendering_proven"])

    def test_real_v120_maps_ui_gate_common_tail(self):
        path = ROOT / "evidence/retail_frontier_20261019/ui_gate_common_tail_dispatch.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["format"], "SHIFT.RetailUiGateCommonTailDispatch/1")
        self.assertEqual(record["probe"]["frames_rendered"], 120)
        self.assertEqual(record["probe"]["gate_calls"], 121)
        self.assertEqual(record["probe"]["gate_return_eax"], "0x00000000")
        self.assertEqual(record["probe"]["calls_per_mapping"], 121)
        self.assertEqual(
            [call["target_inner_device_method"] for call in record["tail_calls"]],
            ["IDirect3DDevice9::EndScene", "IDirect3DDevice9::Present"],
        )
        self.assertTrue(all(call["count"] == 121 for call in record["tail_calls"]))
        self.assertIn("does not demonstrate", record["interpretation"])

    def test_v281_effect_capture_records_metadata_without_binary_payload(self):
        path = ROOT / "evidence/retail_frontier_20261019/entrypoint_probe_v281_d3dx_effect_capture.json"
        raw = path.read_text(encoding="utf-8")
        record = json.loads(raw)
        self.assertEqual(record["format"], "SHIFT.RetailD3DXEffectFrontier/1")
        self.assertEqual(record["probe"]["status"], "blocked")
        self.assertEqual(record["probe"]["dispatches"], 526429)
        self.assertEqual(record["effect_input"]["size_bytes"], 1984)
        self.assertEqual(
            record["effect_input"]["sha256"],
            "74901707d164f3014e8dc72da7232b1076d003ae3288535ca7c8376aec923fa9",
        )
        self.assertEqual(record["binary_effect_structure"]["technique"], "ShadowGen")
        self.assertEqual(
            record["caller_contract"]["first_effect_method"],
            "ID3DXEffect::FindNextValidTechnique",
        )
        self.assertNotIn("source_hex", raw)
        self.assertFalse(record["binary_effect_structure"]["shader_bytecode_committed"])

    def test_v290_decoder_record_keeps_static_and_runtime_evidence_separate(self):
        path = ROOT / "evidence/retail_frontier_20261019/entrypoint_probe_v290_decoder_framing.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["format"], "SHIFT.RetailDecoderFraming/1")
        self.assertEqual(record["wrapper"]["address"], "0x0066f680")
        self.assertEqual(record["wrapper"]["input_framing"]["reserved_trailing_bytes"], 5)
        self.assertEqual(record["runtime_probes"][1]["status"], "timeout")
        self.assertFalse(record["runtime_probes"][1]["guest_decoder_breakpoint_hit"])
        self.assertFalse(record["interpretation"]["adapter_ready"])

    def test_v291_records_no_frontier_before_manual_kill(self):
        path = ROOT / "evidence/retail_frontier_20261019/entrypoint_probe_v291_decode_call_trace.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["format"], "SHIFT.RetailStartupFrontier/1")
        self.assertEqual(record["status"], "unknown")
        self.assertEqual(record["exit_code"], 137)
        self.assertTrue(record["pe_image_loaded"])
        self.assertIsNone(record["dispatches"])
        self.assertEqual(record["comparison"]["result"], "unverified")

    def test_v292_records_live_decoder_stack_without_claiming_capture(self):
        path = ROOT / "evidence/retail_frontier_20261019/entrypoint_probe_v292_decoder_live_stack.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["format"], "SHIFT.RetailDecoderLiveStack/1")
        self.assertEqual(record["probe"]["status"], "timeout")
        self.assertEqual(record["probe"]["exit_code"], 124)
        self.assertIsNone(record["probe"]["guest_dispatch_count"])
        self.assertTrue(record["live_snapshot"]["artifact_sha256"])
        self.assertTrue(record["interpretation"]["decoder_wrapper_active"])
        self.assertFalse(record["interpretation"]["stack_arguments_captured"])
        self.assertFalse(record["interpretation"]["compressed_bytes_captured"])
        self.assertFalse(record["interpretation"]["offline_gameplay_proven"])

    def test_timeout_marker_classifies_forced_kill_as_timeout(self):
        log = (
            "Loaded PE32 image into P-code guest RAM\n"
            "retail_probe_timeout: seconds=30 kill_after_seconds=5 exit_code=137\n"
        )
        result = frontier.inspect_log(log, 137)
        self.assertEqual(result["status"], "timeout")
        self.assertTrue(result["pe_image_loaded"])
        self.assertIsNone(result["dispatches"])

    def test_frame_loop_is_not_retail_rendering(self):
        data = {
            "format": "SHIFT.NativeRuntimeFrameLoop/1",
            "frames_rendered": 1800,
            "validation_errors": 0,
            "recompiled_pe_image_loaded": True,
            "recompiled_pcode_functions_dispatched": 342703,
            "recompiled_pcode_unique_functions_dispatched": 1417,
            "d3d9_vulkan_bridge": {"present_submissions": 3},
        }
        report = frontier.inspect_log(json.dumps(data) + "\n", 0)
        self.assertEqual(report["status"], "host-frame-loop")
        self.assertEqual(report["frames_rendered"], 1800)
        self.assertEqual(report["d3d9_vulkan_bridge"]["present_submissions"], 3)
        self.assertFalse(report["retail_rendering_proven"])

    def test_comparison_advancement_and_regression(self):
        old = {"status": "blocked", "dispatches": 49065,
               "unique_functions": 1249, "blocker": "D3DXCreateTexture"}
        improved = dict(old, dispatches=50000, unique_functions=1270)
        self.assertEqual(frontier.compare(improved, old)["result"], "advanced")
        self.assertEqual(frontier.compare(old, old)["result"], "unchanged")
        degraded = dict(old, dispatches=48000)
        self.assertEqual(frontier.compare(degraded, old)["result"], "regressed")
        invalid = dict(old, status="timeout")
        self.assertEqual(frontier.compare(invalid, old)["result"], "unverified")
        validation = dict(old, validation_errors=1)
        self.assertEqual(frontier.compare(validation, old)["result"], "regressed")
        changed = dict(old, blocker="unknown other error")
        self.assertEqual(frontier.compare(changed, old)["result"], "changed")

    def test_cli_inspect_and_json_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            log = folder / "failed.log"
            log.write_text(
                "Loaded PE32 image into P-code guest RAM\n"
                "shift_runtime: recompiled PE32 entry point 0x0090488a failed "
                "after 12 P-code function dispatches across 7 unique functions: "
                "unimplemented PE import d3d9.dll!GetDeviceCaps;\n",
                encoding="utf-8",
            )
            output = folder / "frontier.json"
            cmd = [sys.executable, str(ROOT / "tools/retail_frontier.py"),
                   "inspect", "--log", str(log), "--output", str(output)]
            subprocess.run(cmd, check=True, capture_output=True)
            baseline = folder / "baseline.json"
            baseline.write_text(output.read_text(encoding="utf-8"), encoding="utf-8")
            proc = subprocess.run(cmd + ["--baseline", str(baseline)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(output.read_text())["comparison"]["result"],
                             "unchanged")
            wrong = folder / "wrong-baseline.json"
            wrong.write_text('{"format":"unrelated"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                frontier.load_frontier(wrong)

    def test_module_manifest_verifies_paths_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            override = artifacts / "override.so"
            supplement = artifacts / "nested" / "supplement.so"
            supplement.parent.mkdir()
            override.write_bytes(b"override fixture")
            supplement.write_bytes(b"supplement fixture")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "execution_evidence": {
                    "additional_overrides": [{
                        "path": "override.so", "sha256": frontier.sha256(override),
                    }],
                    "additional_supplements": [{
                        "path": "nested/supplement.so",
                        "sha256": frontier.sha256(supplement),
                    }],
                },
            }), encoding="utf-8")

            loaded = frontier.load_module_manifest(manifest, artifacts)
            self.assertEqual(loaded["overrides"], [str(override.resolve())])
            self.assertEqual(loaded["supplements"], [str(supplement.resolve())])
            self.assertEqual(loaded["evidence"]["overrides"][0]["path"], "override.so")
            self.assertEqual(loaded["evidence"]["supplements"][0]["path"],
                             "nested/supplement.so")

            (artifacts / "override.so").write_bytes(b"changed override")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                frontier.load_module_manifest(manifest, artifacts)

    def test_module_manifest_rejects_paths_outside_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            outside = root / "outside.so"
            outside.write_bytes(b"outside")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "execution_evidence": {
                    "additional_supplements": [{
                        "path": "../outside.so", "sha256": frontier.sha256(outside),
                    }],
                },
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes or is missing"):
                frontier.load_module_manifest(manifest, artifacts)

    def test_manifest_modules_append_without_discarding_existing_probe_modules(self):
        env = {"SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS": "/external/already-selected.so"}
        frontier._append_paths(
            env, "SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS",
            ["/external/new.so", "/external/already-selected.so"],
        )
        self.assertEqual(
            env["SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS"].splitlines(),
            ["/external/already-selected.so", "/external/new.so"],
        )

    def test_run_cli_loads_manifest_modules_and_records_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            artifacts = folder / "artifacts"
            artifacts.mkdir()
            supplement = artifacts / "supplement.so"
            supplement.write_bytes(b"supplement fixture")
            manifest = folder / "manifest.json"
            manifest.write_text(json.dumps({
                "execution_evidence": {
                    "additional_supplements": [{
                        "path": "supplement.so",
                        "sha256": frontier.sha256(supplement),
                    }],
                },
            }), encoding="utf-8")
            runtime = folder / "shift_runtime"
            runtime.touch()
            pe = folder / "SHIFT.exe"
            pe.write_bytes(b"retail fixture")
            game_data = folder / "game-data"
            game_data.mkdir()
            log = folder / "probe.log"
            output = folder / "report.json"
            captured = {}

            def fake_run(command, env, check=False):
                captured["supplements"] = env["SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS"]
                captured["kill_after"] = env["SHIFT_ENTRYPOINT_PROBE_KILL_AFTER_SECONDS"]
                Path(command[-1]).write_text(
                    '{"format":"SHIFT.NativeRuntimeFrameLoop/1",'
                    '"frames_rendered":1,"validation_errors":0}\n',
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0)

            with patch.object(frontier, "RETAIL_SHA256", frontier.sha256(pe)), \
                    patch.object(frontier.subprocess, "run", side_effect=fake_run), \
                    patch.dict(os.environ, {
                        "SHIFT_TRACE_GUEST_CALL_TARGETS": "0x00455ba0",
                        "SHIFT_TRACE_GUEST_CALL_STACK_SLOTS": "0x4,0x8",
                        "SHIFT_TRACE_GUEST_CALL_LIVE_LOG": "1",
                        "SHIFT_TRACE_UNRECOGNIZED_TEST_VALUE": "must-not-be-copied",
                    }):
                result = frontier.main([
                    "run", "--runtime", str(runtime), "--artifacts", str(artifacts),
                    "--build-dir", str(folder / "build"), "--pe", str(pe),
                    "--game-data", str(game_data), "--module-manifest", str(manifest),
                    "--frames", "1", "--timeout", "1", "--log", str(log),
                    "--output", str(output),
                ])

            self.assertEqual(result, 0)
            self.assertEqual(captured["supplements"], str(supplement.resolve()))
            self.assertEqual(captured["kill_after"], "5")
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["probe_configuration"]["module_manifest"]["supplements"], [{
                "path": "supplement.so", "sha256": frontier.sha256(supplement),
            }])
            self.assertEqual(report["probe_configuration"]["kill_after_seconds"], 5)
            self.assertEqual(report["probe_configuration"]["trace_environment"], {
                "SHIFT_TRACE_GUEST_CALL_TARGETS": "0x00455ba0",
                "SHIFT_TRACE_GUEST_CALL_STACK_SLOTS": "0x4,0x8",
                "SHIFT_TRACE_GUEST_CALL_LIVE_LOG": "1",
            })

    def test_probe_launcher_kills_runtime_that_ignores_sigterm(self):
        if not shutil.which("timeout"):
            self.skipTest("GNU timeout is required by the Linux retail launcher")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            artifacts = folder / "artifacts"
            artifacts.mkdir()
            script = ROOT / "tools/run_shift_recompiled_entrypoint_probe.sh"
            shell = script.read_text(encoding="utf-8")
            for relative in re.findall(r'\$artifact_root/([^" ]+\.so)', shell):
                module = artifacts / relative
                module.parent.mkdir(parents=True, exist_ok=True)
                module.touch()
            build = folder / "build"
            build.mkdir()
            (build / "libnfs_shift_pcode_frontier.so").touch()
            game_data = folder / "game-data"
            game_data.mkdir()
            mesh = folder / "probe.mgeo"
            mesh.write_bytes(b"MGEO")
            pe = folder / "SHIFT.exe"
            pe.touch()
            runtime = folder / "ignores-term"
            runtime.write_text(
                "#!/usr/bin/env python3\n"
                "import signal, time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                "while True: time.sleep(0.1)\n",
                encoding="utf-8",
            )
            runtime.chmod(0o755)
            log = folder / "probe.log"
            env = os.environ.copy()
            env.update({
                "SHIFT_ENTRYPOINT_TIMEOUT_SECONDS": "1",
                "SHIFT_ENTRYPOINT_PROBE_KILL_AFTER_SECONDS": "1",
                "SHIFT_ENTRYPOINT_PROBE_FRAMES": "1",
                "SHIFT_ENTRYPOINT_PROBE_MESH": str(mesh),
                "SHIFT_ENTRYPOINT_PROBE_PCODE_MODULE": str(
                    artifacts / "libnfs_shift_pcode_startup_20261018.so"
                ),
            })
            completed = subprocess.run(
                ["bash", str(script), str(runtime), str(artifacts), str(build),
                 str(pe), str(game_data), str(log)],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(completed.returncode, 137, completed.stderr)
            report = frontier.inspect_log(log.read_text(encoding="utf-8"),
                                          completed.returncode)
            self.assertEqual(report["status"], "timeout")

    def test_probe_launcher_forwards_extra_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            artifacts = folder / "retail artifacts"
            artifacts.mkdir()
            module = artifacts / "startup.so"
            module.touch()
            overrides = [folder / "fxam.so", folder / "fprem.so"]
            supplements = [folder / "helper.so"]
            for path in [*overrides, *supplements]:
                path.touch()
            runtime = folder / "fake runtime.py"
            runtime.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "open(os.environ['ARGS_CAPTURE'], 'w').write(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            runtime.chmod(0o755)
            game_data = folder / "game data"
            game_data.mkdir()
            mesh = folder / "probe.mgeo"
            mesh.write_bytes(b"MGEO")
            pe = folder / "SHIFT.exe"
            pe.touch()
            capture = folder / "args.json"
            env = os.environ.copy()
            env.update({
                "ARGS_CAPTURE": str(capture),
                "SHIFT_ENTRYPOINT_PROBE_PCODE_MODULE": str(module),
                "SHIFT_ENTRYPOINT_PROBE_MESH": str(mesh),
                "SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES": "\n".join(map(str, overrides)),
                "SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS": str(supplements[0]),
                "SHIFT_ENTRYPOINT_PROBE_FRAMES": "2",
                "SHIFT_ENTRYPOINT_TIMEOUT_SECONDS": "5",
            })
            result = subprocess.run(
                ["bash", str(ROOT / "tools/run_shift_recompiled_entrypoint_probe.sh"),
                 str(runtime), str(artifacts), str(folder / "build"), str(pe),
                 str(game_data), str(folder / "probe.log")],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            args = json.loads(capture.read_text(encoding="utf-8"))
            selected = [args[index + 1] for index, arg in enumerate(args[:-1])
                        if arg == "--recompiled-override"]
            self.assertEqual(selected[-2:], list(map(str, overrides)))
            self.assertIn(str(supplements[0]), args)


class D3D9ComparisonTests(unittest.TestCase):
    def test_pointer_identity_does_not_pollute_contract(self):
        a = {"event": "create_texture", "texture_ptr": "0xaaaa",
             "width": 1024, "height": 4096, "levels": 1, "usage": 1,
             "format": 21, "pool": 0}
        b = dict(a, texture_ptr="0xbbbb", width="0x400")
        self.assertEqual(d3d9.event_contract(a), d3d9.event_contract(b))

    def test_failed_import_is_request_only(self):
        log = (
            "shift_runtime: failed after 49065 P-code function dispatches across "
            "1249 unique functions: unimplemented PE import "
            "d3dx9_41.dll!D3DXCreateTexture; called from 0x008391b0 "
            "args=[0x2001b3f4,0x00000400,0x00001000,0x00000001,"
            "0x00000001,0x00000015,0x00000000,0x27f4a898]"
        )
        events = d3d9.linux_failure_request(log)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["fields"]["width"], 1024)
        self.assertEqual(events[0]["fields"]["height"], 4096)
        self.assertEqual(events[0]["observation"], "request-only")

    def test_subsequence_and_missing(self):
        texture = d3d9.event_contract({
            "event": "create_texture", "width": 1024, "height": 4096,
            "levels": 1, "usage": 1, "format": 21, "pool": 0,
        })
        other = {"event": "clear", "fields": {"clear_flags": 1}}
        matched = d3d9.compare([other, texture], [texture], "jsonl")
        self.assertEqual(matched["status"], "matched-subsequence")
        request = dict(texture, observation="request-only")
        self.assertEqual(d3d9.compare([texture], [request], "probe-diagnostic")["status"],
                         "request-only-match")
        missing = d3d9.compare([other], [texture], "jsonl")
        self.assertEqual(missing["status"], "not-found")
        self.assertEqual(d3d9.compare([], [texture], "jsonl")["status"],
                         "insufficient-evidence")
        self.assertFalse(matched["semantic_parity_proven"])

    def test_cli_parses_retained_v173_log_against_proxy_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proxy = root / "proxy.jsonl"
            proxy.write_text(json.dumps({
                "event": "create_texture", "width": 1024, "height": 4096,
                "levels": 1, "usage": 1, "format": 21, "pool": 0,
                "texture_ptr": "0xdeadbeef",
            }) + "\n", encoding="utf-8")
            candidate = ROOT / "evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log"
            output = root / "result.json"
            cmd = [sys.executable, str(ROOT / "tools/compare_shift_d3d9.py"),
                   "--reference", str(proxy), "--candidate", str(candidate),
                   "--output", str(output), "--strict"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "request-only-match")
            self.assertFalse(data["semantic_parity_proven"])
            proxy.write_text('{"event":"create_texture","width":4}\n', encoding="utf-8")
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
