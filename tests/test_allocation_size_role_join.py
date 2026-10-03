import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "shift_live_dump" / "join_allocation_size_role.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("join_allocation_size_role", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _argument_join(*, size_indices=(0,)):
    arguments = []
    for index in size_indices:
        arguments.append(
            {
                "backend_storage": "EDX:4",
                "forwarding_source": f"input:Stack[0x{4 + index * 4:x}]:4",
                "source_argument_index": index,
                "source_argument_expression": ["count * 0x10", "pool_id", "flags"][index],
                "source_argument_mapped": True,
            }
        )
    return {
        "format": "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1",
        "rows": [
            {
                "caller": "FUN_00100000",
                "wrapper": "FUN_00886900",
                "occurrence": 0,
                "ghidra_direct_edge": True,
                "forwarding_join_ready": True,
                "backend_calls": [
                    {
                        "instruction": "0x00886911",
                        "target": "0x00638020",
                        "target_name": "FUN_00638020",
                        "transfer_kind": "call",
                        "arguments": arguments,
                    }
                ],
            }
        ],
    }


def _slice(*, proven=True, storage="EDX:4"):
    return {
        "format": "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1",
        "allocation_size_role_proven": proven,
        "allocation_size_entry_storage": storage if proven else None,
    }


def test_promotes_only_source_argument_reaching_proven_percent_d_storage(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    diagnostic_slice = tmp_path / "diagnostic_slice.json"
    _write(argument_join, _argument_join())
    _write(diagnostic_slice, _slice())

    report = module.join_allocation_size_role(argument_join, diagnostic_slice)

    assert report["format"] == "SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1"
    assert report["allocation_size_backend_storage"] == "EDX:4"
    assert report["backend_allocation_size_role_proven"] is True
    assert report["allocation_size_role_callsite_count"] == 1
    assert report["allocation_size_source_argument_indices"] == [0]

    row = report["rows"][0]
    assert row["allocation_size_role_proven"] is True
    assert row["allocation_size_source_argument_index"] == 0
    assert row["allocation_size_source_argument_expression"] == "count * 0x10"
    assert row["missing"] == []
    assert row["allocation_size_observations"] == [
        {
            "backend_call_instruction": "0x00886911",
            "backend_target": "0x00638020",
            "backend_storage": "EDX:4",
            "forwarding_source": "input:Stack[0x4]:4",
            "source_argument_index": 0,
            "source_argument_expression": "count * 0x10",
            "source_argument_mapped": True,
        }
    ]
    assert report["scope"]["allocation_size_role_proven"] is True
    assert report["scope"]["pool_selector_role_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_does_not_promote_without_backend_diagnostic_proof(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    diagnostic_slice = tmp_path / "diagnostic_slice.json"
    _write(argument_join, _argument_join())
    _write(diagnostic_slice, _slice(proven=False))

    report = module.join_allocation_size_role(argument_join, diagnostic_slice)

    assert report["backend_allocation_size_role_proven"] is False
    assert report["allocation_size_backend_storage"] is None
    assert report["allocation_size_role_callsite_count"] == 0
    row = report["rows"][0]
    assert row["allocation_size_role_proven"] is False
    assert row["allocation_size_source_argument_index"] is None
    assert "allocation_size_backend_storage_not_proven" in row["missing"]
    assert report["scope"]["allocation_size_role_proven"] is False


def test_conflicting_source_indices_fail_closed(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    diagnostic_slice = tmp_path / "diagnostic_slice.json"
    _write(argument_join, _argument_join(size_indices=(0, 1)))
    _write(diagnostic_slice, _slice())

    report = module.join_allocation_size_role(argument_join, diagnostic_slice)

    row = report["rows"][0]
    assert row["allocation_size_role_proven"] is False
    assert row["allocation_size_source_argument_indices"] == [0, 1]
    assert row["allocation_size_source_argument_index"] is None
    assert "conflicting_source_argument_indices" in row["missing"]
    assert report["allocation_size_role_callsite_count"] == 0


def test_non_allocation_backend_does_not_create_role(tmp_path):
    module = _load_module()
    value = _argument_join()
    value["rows"][0]["backend_calls"][0]["target"] = "0x006382b0"
    argument_join = tmp_path / "argument_join.json"
    diagnostic_slice = tmp_path / "diagnostic_slice.json"
    _write(argument_join, value)
    _write(diagnostic_slice, _slice())

    report = module.join_allocation_size_role(argument_join, diagnostic_slice)
    row = report["rows"][0]
    assert row["allocation_size_role_proven"] is False
    assert row["allocation_size_observations"] == []
    assert "allocation_backend_size_storage_not_observed" in row["missing"]
