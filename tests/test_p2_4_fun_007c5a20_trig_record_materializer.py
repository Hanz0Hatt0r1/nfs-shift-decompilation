import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_007c5a20_trig_record_materializer.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007c5a20_trig_record_materializer.hpp"
CPP = ROOT / "native_runtime/tests/fun_007c5a20_trig_record_materializer_check.cpp"
FRONTIER = ROOT / "src/physics/native_vehicle_external_provider_frontier_p2_4_current.py"


def test_selected_trig_record_materializer_pins_exact_machine_spans() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007c5a20TrigRecordMaterializer/1"
    spans = payload["machine_spans"]
    assert spans["FUN_007c5a20"] == {
        "start": "0x007c5a20",
        "end_exclusive": "0x007c5ab8",
        "size": 152,
        "raw_byte_sha256": "46a5c431c573c83d21c64e135c884f40521cbbbd74724706479fb3541f184713",
    }
    assert spans["FUN_007bf790_selected_record_calls"] == {
        "start": "0x007bf983",
        "end_exclusive": "0x007bf9d3",
        "size": 80,
        "raw_byte_sha256": "12049fc9876432475c2ee2b34705372173dd2e6aec68842a42141ef3a30ea258",
    }


def test_selected_trig_record_materializer_pins_load_object_geometry() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    selected = payload["selected_records"]
    assert selected["load_object_pointer"] == "*(HDVehicle+0x66b4)"
    assert selected["FUN_007bf790_receiver"] == "load_object+0x0fe8"
    assert selected["destination_table_root"] == "HDVehicle+0x4330"
    assert selected["source_vector_offsets_from_load_object"] == ["0x11d0", "0x11e8"]
    assert selected["selector_offsets_from_load_object"] == ["0x13c0", "0x13c8"]
    assert selected["absolute_destination_base_offsets"] == ["0x54b8", "0x5508"]
    assert selected["scale_constant_address"] == "0x00b09258"

    header = HEADER.read_text(encoding="utf-8")
    for literal in ("0x11d0u", "0x11e8u", "0x13c0u", "0x13c8u", "0x1188u", "0x11d8u"):
        assert literal in header


def test_selected_trig_record_materializer_preserves_stateful_zero_source_branch() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    semantics = payload["materializer_semantics"]
    assert semantics["copy_base_and_slope_always"] is True
    assert semantics["zero_source_action"] == "preserve previous destination count"
    assert semantics["selector_conversion"] == "trunc_toward_zero(selector_qword)"

    header = HEADER.read_text(encoding="utf-8")
    assert "result.count = input.previous_count" in header
    assert "if (magnitude_squared > 0.0)" in header
    assert "result.count = fun_007c5a20_truncate_to_i32(input.source[2])" in header
    assert "result.count - 1" in header


def test_selected_trig_record_materializer_keeps_source_ownership_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    ownership = payload["ownership_boundary"]
    assert ownership["load_object_pointer_provenance_known"] is True
    assert ownership["load_object_selected_source_values_internalized"] is False
    assert ownership["load_object_selected_source_lifetime_internalized"] is False
    assert ownership["FUN_007c5a20_complete"] is False
    assert ownership["FUN_007bf790_complete"] is False

    limits = payload["limits"]
    assert limits["positive_qword_producer_family_complete"] is False
    assert limits["FUN_007584f0_computed_payloads_complete"] is False
    assert limits["external_provider_count_after"] == 7
    assert '"FUN_007584f0_computed_payloads"' in FRONTIER.read_text(encoding="utf-8")


def test_selected_trig_record_materializer_cpp_check_compiles_and_runs(tmp_path: Path) -> None:
    compiler = shutil.which("c++") or shutil.which("g++")
    if compiler is None:
        pytest.skip("no C++ compiler available for focused header-only runtime check")

    binary = tmp_path / "fun_007c5a20_trig_record_materializer_check"
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-I",
            str(ROOT / "native_runtime/include"),
            str(CPP),
            "-o",
            str(binary),
        ],
        check=True,
        cwd=ROOT,
    )
    completed = subprocess.run(
        [str(binary)],
        check=True,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert result["format"] == "SHIFT.Fun007c5a20TrigRecordMaterializer/1"
    assert result["ready"] is True
    assert result["zero_source_previous_count_preserved"] is True
    assert result["external_provider_count"] == 7
