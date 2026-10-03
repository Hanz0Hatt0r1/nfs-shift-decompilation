import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_returned_allocation_pointer_return_provenance.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_returned_pointer_return_provenance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_boundary(path, module, targets):
    payload = {
        "format": module.BOUNDARY_FORMAT,
        "return_origin_targets": list(targets),
        "required_instruction_targets": list(targets),
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "vehicle_create_bridges": [
            {
                "descriptor": 2,
                "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                "returned_allocation_pointer_role_state": "unknown",
            }
        ],
        "blockers": [module.EXPECTED_BLOCKER],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _ins(address, mnemonic, operands=None, flows=None, fallthrough=None, pcode=None, text=None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands or [],
        "flows": flows or [],
        "fallthrough": fallthrough,
        "pcode": [{"opcode": opcode} for opcode in (pcode or [])],
        "text": text or mnemonic,
    }


def _row(module, address, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "found": True,
        "requested": address,
        "function": {"address": address, "name": f"FUN_{address[2:]}"},
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_direct_call_result_and_external_tail_become_exact_next_frontier(tmp_path):
    module = _load_module()
    targets = ["0x00639000", "0x0063a000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(
                module,
                targets[0],
                [
                    _ins(
                        "0x00639000",
                        "CALL",
                        ["FUN_00650000"],
                        ["0x00650000"],
                        "0x00639005",
                        ["CALL"],
                    ),
                    _ins("0x00639005", "RET", pcode=["RETURN"]),
                ],
            ),
            _row(
                module,
                targets[1],
                [
                    _ins(
                        "0x0063a000",
                        "JMP",
                        ["FUN_00660000"],
                        ["0x00660000"],
                        None,
                        ["BRANCH"],
                    )
                ],
            ),
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["format"] == module.FORMAT
    assert report["all_target_machine_return_origins_resolved"] is True
    assert report["next_return_origin_targets"] == ["0x00650000", "0x00660000"]
    assert report["returned_allocation_pointer_role_proven"] is False
    first = report["targets"][0]["exits"][0]
    assert first["machine_return_origin_state"] == "verified"
    assert first["origin"]["kind"] == "direct-call-result"
    assert first["origin"]["target"] == "0x00650000"
    second = report["targets"][1]["exits"][0]
    assert second["kind"] == "external-tail-transfer"
    assert second["target"] == "0x00660000"
    assert report["vehicle_create_bridges"][0][
        "returned_pointer_target_machine_return_origins_resolved"
    ] is True


def test_verified_constant_return_does_not_invent_allocator_target(tmp_path):
    module = _load_module()
    targets = ["0x00639000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(
                module,
                targets[0],
                [
                    _ins(
                        "0x00639000",
                        "MOV",
                        ["EAX", "0"],
                        fallthrough="0x00639005",
                        pcode=["COPY"],
                    ),
                    _ins("0x00639005", "RET", pcode=["RETURN"]),
                ],
            )
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is True
    assert report["next_return_origin_targets"] == []
    assert report["targets"][0]["exits"][0]["origin"]["kind"] == "constant"
    assert "returned_pointer_semantics_require_non_call_origin_interpretation" in report["blockers"]
    assert report["returned_allocation_pointer_role_state"] == "unknown"


def test_partial_eax_write_is_fail_closed(tmp_path):
    module = _load_module()
    targets = ["0x00639000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(
                module,
                targets[0],
                [
                    _ins(
                        "0x00639000",
                        "CALL",
                        ["FUN_00650000"],
                        ["0x00650000"],
                        "0x00639005",
                        ["CALL"],
                    ),
                    _ins(
                        "0x00639005",
                        "MOV",
                        ["AL", "1"],
                        fallthrough="0x00639007",
                        pcode=["COPY"],
                    ),
                    _ins("0x00639007", "RET", pcode=["RETURN"]),
                ],
            )
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is False
    assert report["targets"][0]["exits"][0]["origin"]["kind"] == "partial-eax-write"
    assert report["next_return_origin_targets"] == []
    assert "target_machine_return_origin_not_fully_resolved" in report["blockers"]


def test_cfg_merge_with_two_call_origins_is_ambiguous(tmp_path):
    module = _load_module()
    targets = ["0x00639000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(
                module,
                targets[0],
                [
                    _ins(
                        "0x00639000",
                        "JZ",
                        ["0x00639010"],
                        ["0x00639010"],
                        "0x00639005",
                        ["CBRANCH"],
                    ),
                    _ins(
                        "0x00639005",
                        "CALL",
                        ["FUN_00650000"],
                        ["0x00650000"],
                        "0x0063900a",
                        ["CALL"],
                    ),
                    _ins(
                        "0x0063900a",
                        "JMP",
                        ["0x00639020"],
                        ["0x00639020"],
                        None,
                        ["BRANCH"],
                    ),
                    _ins(
                        "0x00639010",
                        "CALL",
                        ["FUN_00660000"],
                        ["0x00660000"],
                        "0x00639015",
                        ["CALL"],
                    ),
                    _ins(
                        "0x00639015",
                        "JMP",
                        ["0x00639020"],
                        ["0x00639020"],
                        None,
                        ["BRANCH"],
                    ),
                    _ins("0x00639020", "RET", pcode=["RETURN"]),
                ],
            )
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is False
    exit_row = report["targets"][0]["exits"][0]
    assert exit_row["machine_return_origin_state"] == "ambiguous"
    assert {item["target"] for item in exit_row["origins"]} == {
        "0x00650000",
        "0x00660000",
    }
    assert report["next_return_origin_targets"] == []


def test_call_requires_structured_pcode_call(tmp_path):
    module = _load_module()
    targets = ["0x00639000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(
                module,
                targets[0],
                [
                    _ins(
                        "0x00639000",
                        "CALL",
                        ["FUN_00650000"],
                        ["0x00650000"],
                        "0x00639005",
                        ["COPY"],
                    ),
                    _ins("0x00639005", "RET", pcode=["RETURN"]),
                ],
            )
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is False
    assert report["targets"][0]["exits"][0]["origin"]["kind"] == "ambiguous-call-result"
    assert report["next_return_origin_targets"] == []


def test_boundary_cannot_preclaim_returned_pointer_semantics(tmp_path):
    module = _load_module()
    targets = ["0x00639000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    payload = json.loads(boundary.read_text(encoding="utf-8"))
    payload["returned_allocation_pointer_role_proven"] = True
    payload["returned_allocation_pointer_role_state"] = "verified"
    boundary.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="must remain unresolved"):
        module._load_boundary(boundary)


def test_instruction_export_must_match_exact_boundary_target_set(tmp_path):
    module = _load_module()
    targets = ["0x00639000", "0x0063a000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(module, "0x00639000", [_ins("0x00639000", "RET", pcode=["RETURN"])]),
            _row(module, "0x0063b000", [_ins("0x0063b000", "RET", pcode=["RETURN"])]),
        ],
    )

    with pytest.raises(ValueError, match="target identity drift"):
        module.analyze_vehicle_returned_allocation_pointer_return_provenance(
            boundary, instructions
        )


def test_missing_return_pcode_blocks_machine_resolution(tmp_path):
    module = _load_module()
    targets = ["0x00639000"]
    boundary = _write_boundary(tmp_path / "boundary.json", module, targets)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [
            _row(
                module,
                targets[0],
                [_ins("0x00639000", "RET", pcode=["COPY"])],
            )
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is False
    assert report["targets"][0]["blockers"] == [
        {"id": "ret-pcode-return-missing", "instruction": "0x00639000"}
    ]
    assert report["returned_allocation_pointer_role_proven"] is False
