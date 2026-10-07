from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_fun_0079b2d0_virtual_dispatch.json"
DOC = ROOT / "docs/PROCESS_1_FUN_0079B2D0_VIRTUAL_DISPATCH.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_process1_virtual_dispatch_contract_is_exact_pc_retail() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Process1Fun0079b2d0VirtualDispatch/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )


def test_final_vtable_promotes_fun_0079b2d0_from_candidate_to_exact_slot() -> None:
    payload = _load()
    table = payload["vtable"]
    assert table["address"] == "0x00b0b744"
    assert table["slot_count_proven"] == 2
    assert table["slots"][0]["target"] == "0x0079bee0"
    assert table["slots"][1] == {
        "slot": 1,
        "offset": "0x4",
        "target": "0x0079b2d0",
        "role": "virtual update implementation",
    }
    assert table["target_pointer_occurrence_count_in_executable"] == 1
    assert table["target_pointer_cell"] == "0x00b0b748"
    assert table["target_pointer_cell_equals_vtable_plus_4"] is True
    assert table["base_slot_4_state"]["slot_4_target"] == "0x00900e65"
    assert table["base_slot_4_state"]["final_override_target"] == "0x0079b2d0"
    assert table["table_machine_span"]["sha256"] == (
        "ce9191514ac44fe254f65909f3918f3d6b7b5a474dfeeb54bc51036b9f16a00e"
    )
    assert table["constructor_store"]["sha256"] == table["destructor_store"]["sha256"]


def test_parent_plus_340_identity_flows_into_queue_and_fiber_slot_4() -> None:
    payload = _load()
    provenance = payload["object_provenance"]
    queue = payload["queue_dispatch"]
    assert provenance["subobject_offset"] == "0x340"
    assert provenance["subobject_constructor"] == "FUN_0079c1c0"
    assert provenance["subobject_destructor"] == "FUN_0079b1d0"
    assert provenance["parent_constructor_machine_span"]["sha256"] == (
        "51b27814cec2a52aaf58891cf2c6772a7568effa38759f72a9ff97bde507951b"
    )
    assert queue["producer"] == "FUN_00713050"
    assert queue["queue_register"] == "FUN_00a62f60"
    assert queue["queue_execute"] == "FUN_00a62940"
    assert queue["fiber_entry"] == "lpStartAddress_00a62710"
    assert queue["source_lines"]["queue_stores_task_pointer"] == 1372909
    assert queue["source_lines"]["fiber_calls_virtual_slot_4"] == 1372416
    assert queue["machine_spans"]["fiber_virtual_slot_4_call"]["call_instruction"] == "0x00a6272c"


def test_dispatch_path_closes_old_ownerless_branch_without_cadence_overclaim() -> None:
    payload = _load()
    assert payload["dispatch_path"] == [
        "FUN_00713050",
        "FUN_00a62f60",
        "FUN_00a62940",
        "lpStartAddress_00a62710",
        "vtable[+0x4]",
        "FUN_0079b2d0",
        "FUN_00770e80",
    ]
    promotion = payload["promotion"]
    assert promotion["virtual_dispatch_edge_proven"] is True
    assert promotion["FUN_0079b2d0_dispatch_ownerless"] is False
    assert promotion["subobject_identity_continuity_proven"] is True
    assert promotion["queue_registration_continuity_proven"] is True
    assert promotion["higher_level_class_semantic_name_proven"] is False
    assert promotion["render_frame_cadence_proven"] is False
    assert promotion["input_control_owner_proven"] is False
    assert payload["next_blocker"]["process"] == 1
    assert payload["next_blocker"]["alternate_branch_indirect_dispatch_proven"] is True


def test_process1_documentation_records_exact_queue_to_virtual_path() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "FUN_00713050" in text
    assert "FUN_00a62f60" in text
    assert "FUN_00a62940" in text
    assert "lpStartAddress_00a62710" in text
    assert "0x00b0b744" in text
    assert "0x00b0b748" in text
    assert "FUN_0079b2d0" in text
    assert "FUN_00770e80" in text
    assert "rendered-frame cadence" in text
