from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_apc_fileio_surface.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_APC_FILEIO_SURFACE.md"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_controller1_apc_fileio_surface.py"


def load_evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_process1_controller1_apc_fileio_evidence_is_hash_locked() -> None:
    payload = load_evidence()
    source = payload["source"]
    assert payload["format"] == "SHIFT.Process1Controller1ApcFileIoSurface/1"
    assert payload["ready"] is True
    assert source["authority"] == "PC retail 1.02"
    assert source["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert source["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert source["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert source["xbox_recomp_required"] is False

    expected_hashes = {
        "async_file_base_vtable_store": "1ee392d6a29f08faaf9326c24d1f188cee4cc4df14c18b5fb6abb3ed451c4861",
        "controller_ctor_base_and_vtable_store": "0f974fb7c7156e0966bf947d9d76f49b0814cc23c29344c42bac1c2e36a9ebda",
        "read_completion_routine": "1c45703b9acea9563b4ac7515762b01ed1778bffec545607cf5577ecf891d97b",
        "write_completion_routine": "55a55c175c1191be6ba25f8b71a855220ebcb4f4c59726e77d4de305a75dc272",
        "shutdown_direct_controller_enqueue_call": "91a70e233ed4ed1b6b4ba732a8d10b9548103273999738b9d32a52506ac29934",
        "controller_enqueue_wrapper": "834a112d58d05fe2735c9e81203f83631c8909dcebac7330ba878363b279ebc9",
        "controller_vtable_prefix": "ac88f516ec848fafc7040188e41583344cae6656e3276c3e302a5613d00e9040",
        "async_file_vtable_prefix": "0a7f5438c4b486e9e2d9566788a515e03b67f81c8f017005cc4a297b4fa94c44",
    }
    spans = payload["machine_spans"]
    assert {name: value["sha256"] for name, value in spans.items()} == expected_hashes


def test_controller1_and_async_file_direct_surfaces_remain_distinct() -> None:
    payload = load_evidence()
    controller = payload["controller1"]
    async_file = payload["async_file_apc"]
    queue = payload["queue_surface"]
    adjudication = payload["adjudication"]

    assert controller["constructor"] == "FUN_006624a0"
    assert controller["base_constructor"] == "FUN_006551b0"
    assert controller["vtable"] == "0x00af0568"
    assert controller["worker"] == "FUN_00662880"
    assert controller["worker_direct_async_file_tokens_present"] is False

    assert async_file["base_constructor"] == "FUN_00652260"
    assert async_file["base_vtable"] == "0x00aef430"
    assert async_file["completion_owner_expression"] == "*(void **)(OVERLAPPED + 0x10)"
    assert async_file["read_continuation"] == "FUN_00652710"
    assert async_file["write_continuation"] == "FUN_006529f0"
    assert controller["vtable_prefix"] != async_file["vtable_prefix"]

    assert queue["direct_controller_enqueue_callsite_count"] == 1
    assert queue["only_direct_controller_enqueue_caller"] == "FUN_006499e8"
    assert queue["render_or_present_direct_controller_enqueue_caller_proven"] is False

    assert adjudication["controller1_and_async_file_object_families_distinct"] is True
    assert adjudication["controller1_worker_directly_initiates_readfileex_proven"] is False
    assert adjudication["controller1_worker_directly_initiates_writefileex_proven"] is False
    assert adjudication["file_completion_directly_targets_controller1_proven"] is False
    assert adjudication["file_completion_returns_to_overlapped_owner_object_proven"] is True
    assert adjudication["direct_render_or_present_to_controller_enqueue_proven"] is False


def test_negative_direct_result_does_not_overclaim_indirect_alias_closure() -> None:
    payload = load_evidence()
    adjudication = payload["adjudication"]
    assert adjudication["indirect_controller1_apc_initiator_alias_ruled_out"] is False
    assert adjudication["generic_queue_alias_from_render_ruled_out"] is False
    assert payload["next_blocker"]["process"] == 1

    doc = DOC.read_text(encoding="utf-8")
    assert "direct-call statement only" in doc
    assert "indirect aliasing is intentionally unresolved" in doc
    assert "must not be interpreted as proving" in doc


def test_analyzer_fails_closed_on_exact_retail_inputs() -> None:
    source = ANALYZER.read_text(encoding="utf-8")
    assert 'SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"' in source
    assert 'EXE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"' in source
    assert 'EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"' in source
    assert 'len(re.findall(r"\\bFUN_00662ee0\\s*\\(", text)) != 2' in source
    assert '"*(void **)(param_3 + 0x10)" not in read_completion' in source
    assert '"*(void **)(param_3 + 0x10)" not in write_completion' in source
