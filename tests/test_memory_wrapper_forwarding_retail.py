import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tools" / "ghidra" / "analyze_memory_wrapper_forwarding_retail.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_memory_wrapper_forwarding_retail", DRIVER)
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


def _retail_rows():
    c0 = [
        _ins("0x008868c0", "PUSH", ["EBP"], fallthrough="0x008868c1"),
        _ins("0x008868c1", "MOV", ["EBP", "ESP"], fallthrough="0x008868c3"),
        _ins("0x008868c3", "XOR", ["EDX", "EDX"], fallthrough="0x008868c5"),
        _ins("0x008868c5", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x008868c8"),
        _ins("0x008868c8", "POP", ["EBP"], fallthrough="0x008868c9"),
        _ins("0x008868c9", "JMP", ["0x006382b0"], flows=["0x006382b0"], target="0x006382b0"),
    ]

    d0 = [
        _ins("0x008868d0", "PUSH", ["EBP"], fallthrough="0x008868d1"),
        _ins("0x008868d1", "MOV", ["EBP", "ESP"], fallthrough="0x008868d3"),
        _ins("0x008868d3", "MOV", ["ECX", "dword ptr [EBP + 0xc]"], fallthrough="0x008868d6"),
        _ins("0x008868d6", "TEST", ["ECX", "ECX"], fallthrough="0x008868d8"),
        _ins("0x008868d8", "JZ", ["0x008868e6"], fallthrough="0x008868da", flows=["0x008868e6"]),
        _ins("0x008868da", "MOV", ["EDX", "dword ptr [EBP + 0x8]"], fallthrough="0x008868dd"),
        _ins("0x008868dd", "PUSH", ["0x0"], fallthrough="0x008868df"),
        _ins("0x008868df", "CALL", ["0x00638020"], fallthrough="0x008868e4", target="0x00638020"),
        _ins("0x008868e4", "POP", ["EBP"], fallthrough="0x008868e5"),
        _ins("0x008868e5", "RET"),
        _ins("0x008868e6", "XOR", ["EDX", "EDX"], fallthrough="0x008868e8"),
        _ins("0x008868e8", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x008868eb"),
        _ins("0x008868eb", "POP", ["EBP"], fallthrough="0x008868ec"),
        _ins("0x008868ec", "JMP", ["0x006382b0"], flows=["0x006382b0"], target="0x006382b0"),
    ]

    f900 = [
        _ins("0x00886900", "PUSH", ["EBP"], fallthrough="0x00886901"),
        _ins("0x00886901", "MOV", ["EBP", "ESP"], fallthrough="0x00886903"),
        _ins("0x00886903", "MOV", ["ECX", "dword ptr [EBP + 0xc]"], fallthrough="0x00886906"),
        _ins("0x00886906", "TEST", ["ECX", "ECX"], fallthrough="0x00886908"),
        _ins("0x00886908", "JZ", ["0x00886918"], fallthrough="0x0088690a", flows=["0x00886918"]),
        _ins("0x0088690a", "MOV", ["EAX", "dword ptr [EBP + 0x10]"], fallthrough="0x0088690d"),
        _ins("0x0088690d", "MOV", ["EDX", "dword ptr [EBP + 0x8]"], fallthrough="0x00886910"),
        _ins("0x00886910", "PUSH", ["EAX"], fallthrough="0x00886911"),
        _ins("0x00886911", "CALL", ["0x00638020"], fallthrough="0x00886916", target="0x00638020"),
        _ins("0x00886916", "POP", ["EBP"], fallthrough="0x00886917"),
        _ins("0x00886917", "RET"),
        _ins("0x00886918", "MOV", ["EDX", "dword ptr [EBP + 0x10]"], fallthrough="0x0088691b"),
        _ins("0x0088691b", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x0088691e"),
        _ins("0x0088691e", "POP", ["EBP"], fallthrough="0x0088691f"),
        _ins("0x0088691f", "JMP", ["0x006382b0"], flows=["0x006382b0"], target="0x006382b0"),
    ]

    f930 = [
        _ins("0x00886930", "PUSH", ["EBP"], fallthrough="0x00886931"),
        _ins("0x00886931", "MOV", ["EBP", "ESP"], fallthrough="0x00886933"),
        _ins("0x00886933", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x00886936"),
        _ins("0x00886936", "TEST", ["ECX", "ECX"], fallthrough="0x00886938"),
        _ins("0x00886938", "JZ", ["0x00886940"], fallthrough="0x0088693a", flows=["0x00886940"]),
        _ins("0x0088693a", "POP", ["EBP"], fallthrough="0x0088693b"),
        _ins("0x0088693b", "JMP", ["0x0064f4c0"], flows=["0x0064f4c0"], target="0x0064f4c0"),
        _ins("0x00886940", "POP", ["EBP"], fallthrough="0x00886941"),
        _ins("0x00886941", "RET"),
    ]

    f950 = [
        _ins("0x00886950", "PUSH", ["EBP"], fallthrough="0x00886951"),
        _ins("0x00886951", "MOV", ["EBP", "ESP"], fallthrough="0x00886953"),
        _ins("0x00886953", "MOV", ["ECX", "dword ptr [EBP + 0x8]"], fallthrough="0x00886956"),
        _ins("0x00886956", "TEST", ["ECX", "ECX"], fallthrough="0x00886958"),
        _ins("0x00886958", "JZ", ["0x00886971"], fallthrough="0x0088695a", flows=["0x00886971"]),
        _ins("0x0088695a", "MOV", ["EAX", "dword ptr [EBP + 0xc]"], fallthrough="0x0088695d"),
        _ins("0x0088695d", "TEST", ["EAX", "EAX"], fallthrough="0x0088695f"),
        _ins("0x0088695f", "JZ", ["0x0088696b"], fallthrough="0x00886961", flows=["0x0088696b"]),
        _ins("0x00886961", "MOV", ["EDX", "ECX"], fallthrough="0x00886963"),
        _ins("0x00886963", "MOV", ["ECX", "EAX"], fallthrough="0x00886965"),
        _ins("0x00886965", "POP", ["EBP"], fallthrough="0x00886966"),
        _ins("0x00886966", "JMP", ["0x0064f260"], flows=["0x0064f260"], target="0x0064f260"),
        _ins("0x0088696b", "POP", ["EBP"], fallthrough="0x0088696c"),
        _ins("0x0088696c", "JMP", ["0x0064f4c0"], flows=["0x0064f4c0"], target="0x0064f4c0"),
        _ins("0x00886971", "POP", ["EBP"], fallthrough="0x00886972"),
        _ins("0x00886972", "RET"),
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


def test_retail_tail_calls_recover_all_five_wrappers(tmp_path):
    module = _load_module()
    source = tmp_path / "memory_wrapper_instructions.jsonl"
    _write_jsonl(source, _retail_rows())

    report = module.analyze_memory_wrapper_forwarding_retail(source)
    assert report["confirmed_wrapper_forwarding_count"] == 5
    assert report["all_wrapper_forwarding_confirmed"] is True
    assert report["tail_call_modeling"]["tail_call_count"] == 6
    assert report["tail_call_modeling"]["raw_instruction_export_modified"] is False

    c0 = _site(_wrapper(report, "FUN_008868c0"), "0x006382b0")
    assert c0["transfer_kind"] == "tail-call"
    assert [arg["source"] for arg in c0["arguments"]] == [
        "input:Stack[0x4]:4",
        "constant:0x0",
    ]

    d0 = _wrapper(report, "FUN_008868d0")
    assert [arg["source"] for arg in _site(d0, "0x00638020")["arguments"]] == [
        "input:Stack[0x8]:4",
        "input:Stack[0x4]:4",
        "constant:0x0",
    ]
    assert [arg["source"] for arg in _site(d0, "0x006382b0")["arguments"]] == [
        "input:Stack[0x4]:4",
        "constant:0x0",
    ]

    f900 = _wrapper(report, "FUN_00886900")
    assert [arg["source"] for arg in _site(f900, "0x00638020")["arguments"]] == [
        "input:Stack[0x8]:4",
        "input:Stack[0x4]:4",
        "input:Stack[0xc]:4",
    ]
    assert [arg["source"] for arg in _site(f900, "0x006382b0")["arguments"]] == [
        "input:Stack[0x4]:4",
        "input:Stack[0xc]:4",
    ]

    f930 = _site(_wrapper(report, "FUN_00886930"), "0x0064f4c0")
    assert [arg["source"] for arg in f930["arguments"]] == [
        "input:Stack[0x4]:4",
        "input:DL:1",
    ]

    f950 = _wrapper(report, "FUN_00886950")
    assert [arg["source"] for arg in _site(f950, "0x0064f260")["arguments"]] == [
        "input:Stack[0x8]:4",
        "input:Stack[0x4]:4",
    ]
    assert [arg["source"] for arg in _site(f950, "0x0064f4c0")["arguments"]] == [
        "input:Stack[0x4]:4",
        "input:DL:1",
    ]

    assert report["scope"]["argument_semantic_roles_proven"] is False
    assert report["scope"]["ghidra_declared_parameter_semantics_trusted"] is False
