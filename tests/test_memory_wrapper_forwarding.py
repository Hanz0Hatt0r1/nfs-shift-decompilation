import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "analyze_memory_wrapper_forwarding.py"
    spec = importlib.util.spec_from_file_location("analyze_memory_wrapper_forwarding", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic, operands=None, *, fallthrough=None, flows=None, target=None):
    references = []
    if target is not None:
        references.append({"to": target, "type": "UNCONDITIONAL_CALL"})
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": " ".join([mnemonic] + list(operands or [])),
        "operands": list(operands or []),
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": list(flows or ([] if target is None else [target])),
        "references": references,
    }


def _row(address, name, convention, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": name,
            "size": len(instructions),
            "calling_convention": convention,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture_rows():
    c0 = [
        _ins("0x008868c0", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x008868c1"),
        _ins("0x008868c1", "MOV", ["EDX", "0x4"], fallthrough="0x008868c2"),
        _ins("0x008868c2", "CALL", ["0x006382b0"], fallthrough="0x008868c3", target="0x006382b0"),
        _ins("0x008868c3", "RET"),
    ]

    d0 = [
        _ins("0x008868d0", "PUSH", ["0x4"], fallthrough="0x008868d1"),
        _ins("0x008868d1", "MOV", ["ECX", "dword ptr [ESP + 0x8]"], fallthrough="0x008868d2"),
        _ins("0x008868d2", "MOV", ["EDX", "dword ptr [ESP + 0xc]"], fallthrough="0x008868d3"),
        _ins("0x008868d3", "CALL", ["0x00638020"], fallthrough="0x008868d4", target="0x00638020"),
        _ins("0x008868d4", "TEST", ["EAX", "EAX"], fallthrough="0x008868d5"),
        _ins("0x008868d5", "JNZ", ["0x008868da"], fallthrough="0x008868d6", flows=["0x008868da"]),
        _ins("0x008868d6", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x008868d7"),
        _ins("0x008868d7", "MOV", ["EDX", "0x4"], fallthrough="0x008868d8"),
        _ins("0x008868d8", "CALL", ["0x006382b0"], fallthrough="0x008868da", target="0x006382b0"),
        _ins("0x008868da", "RET"),
    ]

    f900 = [
        _ins("0x00886900", "PUSH", ["dword ptr [ESP + 0xc]"], fallthrough="0x00886901"),
        _ins("0x00886901", "MOV", ["ECX", "dword ptr [ESP + 0x8]"], fallthrough="0x00886902"),
        _ins("0x00886902", "MOV", ["EDX", "dword ptr [ESP + 0xc]"], fallthrough="0x00886903"),
        _ins("0x00886903", "CALL", ["0x00638020"], fallthrough="0x00886904", target="0x00638020"),
        _ins("0x00886904", "TEST", ["EAX", "EAX"], fallthrough="0x00886905"),
        _ins("0x00886905", "JNZ", ["0x0088690a"], fallthrough="0x00886906", flows=["0x0088690a"]),
        _ins("0x00886906", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x00886907"),
        _ins("0x00886907", "MOV", ["EDX", "dword ptr [ESP + 0xc]"], fallthrough="0x00886908"),
        _ins("0x00886908", "CALL", ["0x006382b0"], fallthrough="0x0088690a", target="0x006382b0"),
        _ins("0x0088690a", "RET"),
    ]

    f930 = [
        _ins("0x00886930", "CALL", ["0x0064f4c0"], fallthrough="0x00886931", target="0x0064f4c0"),
        _ins("0x00886931", "RET"),
    ]

    f950 = [
        _ins("0x00886950", "MOV", ["ESI", "ECX"], fallthrough="0x00886951"),
        _ins("0x00886951", "MOV", ["EDX", "dword ptr [ESP + 0x4]"], fallthrough="0x00886952"),
        _ins("0x00886952", "CALL", ["0x0064f260"], fallthrough="0x00886953", target="0x0064f260"),
        _ins("0x00886953", "MOV", ["ECX", "ESI"], fallthrough="0x00886954"),
        _ins("0x00886954", "MOV", ["DL", "byte ptr [ESP + 0x8]"], fallthrough="0x00886955"),
        _ins("0x00886955", "CALL", ["0x0064f4c0"], fallthrough="0x00886956", target="0x0064f4c0"),
        _ins("0x00886956", "RET"),
    ]

    return [
        _row("0x008868c0", "FUN_008868c0", "__cdecl", c0),
        _row("0x008868d0", "FUN_008868d0", "__cdecl", d0),
        _row("0x00886900", "FUN_00886900", "__cdecl", f900),
        _row("0x00886930", "FUN_00886930", "__fastcall", f930),
        _row("0x00886950", "FUN_00886950", "__fastcall", f950),
    ]


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _wrapper(report, name):
    return next(row for row in report["wrappers"] if row["name"] == name)


def _site(wrapper, target):
    return next(row for row in wrapper["call_sites"] if row["target"] == target)


def test_recovers_entry_storage_constants_and_fastcall_stack_cleanup(tmp_path):
    module = _load_module()
    source = tmp_path / "memory_wrapper_instructions.jsonl"
    _write_jsonl(source, _fixture_rows())

    report = module.analyze_memory_wrapper_forwarding(source)
    assert report["format"] == "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
    assert report["confirmed_wrapper_forwarding_count"] == 5
    assert report["all_wrapper_forwarding_confirmed"] is True

    d0 = _wrapper(report, "FUN_008868d0")
    first = _site(d0, "0x00638020")
    assert [arg["source"] for arg in first["arguments"]] == [
        "input:Stack[0x4]:4",
        "input:Stack[0x8]:4",
        "constant:0x4",
    ]
    fallback = _site(d0, "0x006382b0")
    # This is only correct if the fastcall stack argument from FUN_00638020 was
    # accounted for when ESP is restored before the fallback path.
    assert fallback["arguments"][0]["source"] == "input:Stack[0x4]:4"

    f900 = _wrapper(report, "FUN_00886900")
    first = _site(f900, "0x00638020")
    assert [arg["source"] for arg in first["arguments"]] == [
        "input:Stack[0x4]:4",
        "input:Stack[0x8]:4",
        "input:Stack[0xc]:4",
    ]

    f930 = _wrapper(report, "FUN_00886930")
    release = _site(f930, "0x0064f4c0")
    assert [arg["source"] for arg in release["arguments"]] == [
        "input:ECX:4",
        "input:DL:1",
    ]

    f950 = _wrapper(report, "FUN_00886950")
    first_release = _site(f950, "0x0064f260")
    assert [arg["source"] for arg in first_release["arguments"]] == [
        "input:ECX:4",
        "input:Stack[0x4]:4",
    ]
    second_release = _site(f950, "0x0064f4c0")
    assert [arg["source"] for arg in second_release["arguments"]] == [
        "input:ECX:4",
        "input:Stack[0x8]:4",
    ]
    assert report["scope"]["argument_semantic_roles_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_unsupported_instruction_poison_is_fail_closed(tmp_path):
    module = _load_module()
    rows = _fixture_rows()
    c0 = rows[0]
    c0["instructions"].insert(
        2,
        _ins("0x008868c15", "XCHG", ["ECX", "EAX"], fallthrough="0x008868c2"),
    )
    c0["instructions"][1]["fallthrough"] = "0x008868c15"
    c0["instruction_count"] = len(c0["instructions"])
    source = tmp_path / "memory_wrapper_instructions.jsonl"
    _write_jsonl(source, rows)

    report = module.analyze_memory_wrapper_forwarding(source)
    wrapper = _wrapper(report, "FUN_008868c0")
    assert wrapper["forwarding_confirmed"] is False
    site = _site(wrapper, "0x006382b0")
    assert site["incoming_state_uncertain"] is True
    assert any("outside the modeled x86 subset" in reason for reason in site["uncertainty_reasons"])
    assert report["all_wrapper_forwarding_confirmed"] is False


def test_conflicting_branch_sources_merge_to_unresolved(tmp_path):
    module = _load_module()
    rows = _fixture_rows()
    c0 = rows[0]
    c0["instructions"] = [
        _ins("0x008868c0", "CMP", ["EAX", "0"], fallthrough="0x008868c1"),
        _ins("0x008868c1", "JNZ", ["0x008868c4"], fallthrough="0x008868c2", flows=["0x008868c4"]),
        _ins("0x008868c2", "MOV", ["ECX", "dword ptr [ESP + 0x4]"], fallthrough="0x008868c3"),
        _ins("0x008868c3", "JMP", ["0x008868c5"], flows=["0x008868c5"]),
        _ins("0x008868c4", "MOV", ["ECX", "0x20"], fallthrough="0x008868c5"),
        _ins("0x008868c5", "MOV", ["EDX", "0x4"], fallthrough="0x008868c6"),
        _ins("0x008868c6", "CALL", ["0x006382b0"], fallthrough="0x008868c7", target="0x006382b0"),
        _ins("0x008868c7", "RET"),
    ]
    c0["instruction_count"] = len(c0["instructions"])
    source = tmp_path / "memory_wrapper_instructions.jsonl"
    _write_jsonl(source, rows)

    report = module.analyze_memory_wrapper_forwarding(source)
    wrapper = _wrapper(report, "FUN_008868c0")
    site = _site(wrapper, "0x006382b0")
    assert site["arguments"][0]["source"] == "unresolved"
    assert site["arguments"][0]["resolved"] is False
    assert wrapper["forwarding_confirmed"] is False


def test_requires_all_five_wrapper_records(tmp_path):
    module = _load_module()
    source = tmp_path / "memory_wrapper_instructions.jsonl"
    _write_jsonl(source, _fixture_rows()[:-1])

    try:
        module.analyze_memory_wrapper_forwarding(source)
    except ValueError as exc:
        assert "instruction export missing wrappers" in str(exc)
        assert "0x00886950" in str(exc)
    else:
        raise AssertionError("missing wrapper export must fail")
