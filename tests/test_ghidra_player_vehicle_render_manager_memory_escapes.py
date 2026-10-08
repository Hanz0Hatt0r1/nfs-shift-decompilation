from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_memory_escapes.py"
SPEC = importlib.util.spec_from_file_location("analyze_player_vehicle_render_manager_memory_escapes", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _state(marker: str, register: str = "ESI"):
    state = {name: frozenset((f"other:{name}",)) for name in m._v1._TRACKED}
    state[register] = frozenset((marker,))
    return state


def _ins(address: str, destination: str, source: str):
    return {
        "address": address,
        "mnemonic": "MOV",
        "operands": [destination, source],
        "text": f"MOV {destination},{source}",
        "pcode": [],
        "flows": [],
    }


def test_detects_stack_and_object_memory_stores():
    marker = "candidate-global-manager:0x00410000@0x00410010"
    stack = m._memory_store_sinks(
        "0x00410000", marker, _ins("0x00410020", "dword ptr [EBP-0x4]", "ESI"), _state(marker)
    )
    assert len(stack) == 1
    assert stack[0]["destination_kind"] == "stack-memory"
    assert stack[0]["destination_base_register"] == "EBP"
    assert stack[0]["destination_displacement"] == -4

    obj = m._memory_store_sinks(
        "0x00410000", marker, _ins("0x00410024", "dword ptr [EDI+0x20]", "ESI"), _state(marker)
    )
    assert len(obj) == 1
    assert obj[0]["destination_kind"] == "register-relative-memory"
    assert obj[0]["destination_base_register"] == "EDI"
    assert obj[0]["destination_displacement"] == 0x20


def test_detects_absolute_store_and_rejects_non_exact_source():
    marker = "candidate-global-manager:0x00410000@0x00410010"
    absolute = m._memory_store_sinks(
        "0x00410000", marker, _ins("0x00410028", "dword ptr [0x00c00000]", "ESI"), _state(marker)
    )
    assert len(absolute) == 1
    assert absolute[0]["destination_kind"] == "absolute-memory"
    assert absolute[0]["destination_displacement"] == 0x00C00000

    non_exact = _state(marker)
    non_exact["ESI"] = frozenset((marker, "joined-other-path"))
    assert m._memory_store_sinks(
        "0x00410000", marker, _ins("0x0041002c", "dword ptr [EDI]", "ESI"), non_exact
    ) == []


def test_non_mov_or_register_destination_is_not_a_store_sink():
    marker = "candidate-global-manager:0x00410000@0x00410010"
    state = _state(marker)
    register_destination = _ins("0x00410030", "EAX", "ESI")
    assert m._memory_store_sinks("0x00410000", marker, register_destination, state) == []
    push = {"address": "0x00410034", "mnemonic": "PUSH", "operands": ["ESI"], "text": "PUSH ESI"}
    assert m._memory_store_sinks("0x00410000", marker, push, state) == []


def test_build_surface_patches_existing_cfg_sink_collection_and_restores(monkeypatch, tmp_path: Path):
    original = m._v1._other_sinks
    marker = "candidate-global-manager:0x00410000@0x00410010"

    def fake_build(*args, **kwargs):
        sinks = m._v1._other_sinks(
            "0x00410000",
            marker,
            _ins("0x00410040", "dword ptr [EDI+0x30]", "ESI"),
            _state(marker),
        )
        return {
            "format": m.UPSTREAM_FORMAT,
            "ready": True,
            "provenance": {
                "seedable_pointer_load_count": 1,
                "reference_read_count": 1,
                "selected_function_count": 1,
            },
            "analysis": {"all_sinks": sinks},
        }

    monkeypatch.setattr(m._v2, "build_frontier", fake_build)
    report = m.build_surface(tmp_path / "identity.json", tmp_path / "rank.json", tmp_path / "instructions.jsonl")

    assert m._v1._other_sinks is original
    assert report["format"] == m.FORMAT
    assert report["analysis"]["memory_store_count"] == 1
    assert report["analysis"]["destination_kind_counts"] == {"register-relative-memory": 1}
    assert report["handoff"]["exact_manager_memory_store_surface_closed_negative"] is False
    assert report["handoff"]["cross_function_persistent_alias_identity_ready"] is False
    assert report["handoff"]["external_provider_count"] == 7
