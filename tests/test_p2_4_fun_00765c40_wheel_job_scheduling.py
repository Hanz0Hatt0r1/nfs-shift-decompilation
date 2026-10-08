import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_wheel_job_scheduling.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_wheel_job_scheduling.hpp"
CMAKE = ROOT / "native_runtime/cmake/p2_4_fun_00765c40.cmake"
DOC = ROOT / "docs/P2_4_FUN_00765C40_WHEEL_JOB_SCHEDULING.md"


def test_wheel_job_scheduling_contract_is_exact_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40WheelJobScheduling/1"
    assert payload["ready"] is True

    surface = payload["retail_surface"]
    assert surface["queue"] == "HDVehicle+0x6730"
    assert surface["registered_wheel_object_count"] == 4
    assert surface["wheel_job_virtual_slot"] == "+0x04"
    assert surface["wheel_job_entry"] == "0x0075cfb0"
    assert surface["load_offsets"] == ["+0x0b38", "+0x15b8", "+0x2038", "+0x2ab8"]
    assert surface["queue_executes_before_load_term_reads"] is True
    assert surface["wheel_job_formula_internalized"] is False
    assert surface["scheduler_argument_semantics_proven"] is False

    native = payload["native_consumption"]
    assert native["queue_executor_is_explicit_boundary"] is True
    assert native["load_term_reader_is_explicit_boundary"] is True
    assert native["queue_called_exactly_once"] is True
    assert native["four_load_terms_read_after_queue"] is True
    assert native["load_terms_validated_finite"] is True
    assert native["wheel_job_formula_internalized"] is False

    scope = payload["scope"]
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_native_header_pins_queue_boundary_and_order() -> None:
    text = HEADER.read_text()
    assert "SHIFT.Fun00765c40WheelJobScheduling/1" in text
    assert "0x6730u" in text
    assert "0x0075cfb0u" in text
    assert "kFun00765c40WheelJobVirtualSlot = 0x04u" in text
    assert "execute_queue();" in text
    assert "read_load_term(wheel)" in text
    assert "validate_fun_00765c40_load_terms" in text
    assert "WheelJobQueueExecution" in text


def test_stable_p2_4_cmake_and_docs_keep_formula_external() -> None:
    cmake = CMAKE.read_text()
    assert "shift_runtime_fun_00765c40_wheel_job_scheduling_check" in cmake
    assert "native-physics-phase" not in cmake

    doc = DOC.read_text()
    assert "FUN_0075cfb0` producer arithmetic: remains external" in doc
    assert "external provider count: remains 7" in doc
