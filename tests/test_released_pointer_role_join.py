import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "shift_live_dump" / "join_released_pointer_role.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("join_released_pointer_role", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_argument_join(path: Path, *, ready=True):
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1",
                "rows": [
                    {
                        "caller": "FUN_00100000",
                        "wrapper": "FUN_00886930",
                        "occurrence": 0,
                        "ghidra_direct_edge": True,
                        "forwarding_join_ready": ready,
                        "forwarding_input_storage": ["ECX:4", "DL:1", "Stack[0x4]:4"],
                        "arguments": [
                            {"expression": "ctx"},
                            {"expression": "flag"},
                            {"expression": "pointer_value"},
                        ],
                    },
                    {
                        "caller": "FUN_00200000",
                        "wrapper": "FUN_00886950",
                        "occurrence": 1,
                        "ghidra_direct_edge": True,
                        "forwarding_join_ready": ready,
                        "forwarding_input_storage": [
                            "ECX:4",
                            "DL:1",
                            "Stack[0x4]:4",
                            "Stack[0x8]:4",
                        ],
                        "arguments": [
                            {"expression": "ctx2"},
                            {"expression": "flag2"},
                            {"expression": "released_object"},
                            {"expression": "alternate_owner"},
                        ],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_chain(path: Path, *, proven=True, conflict=False):
    paths = [
        {
            "wrapper": "FUN_00886930",
            "wrapper_input_storage": "Stack[0x4]:4",
            "released_pointer_path_proven": proven,
        },
        {
            "wrapper": "FUN_00886950",
            "wrapper_input_storage": "Stack[0x4]:4",
            "released_pointer_path_proven": proven,
        },
    ]
    if conflict:
        paths.append(
            {
                "wrapper": "FUN_00886950",
                "wrapper_input_storage": "Stack[0x8]:4",
                "released_pointer_path_proven": True,
            }
        )
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1",
                "release_pointer_to_wrapper_storage_proven": proven,
                "wrapper_paths": paths,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_join_promotes_released_pointer_source_arguments(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    chain = tmp_path / "release_chain.json"
    _write_argument_join(argument_join)
    _write_chain(chain)

    report = module.join_released_pointer_role(argument_join, chain)

    assert report["backend_release_pointer_role_proven"] is True
    assert report["released_pointer_role_callsite_count"] == 2
    assert report["released_pointer_source_argument_indices"] == [2]
    first, second = report["rows"]
    assert first["released_pointer_role_proven"] is True
    assert first["released_pointer_source_argument_index"] == 2
    assert first["released_pointer_source_argument_expression"] == "pointer_value"
    assert second["released_pointer_role_proven"] is True
    assert second["released_pointer_source_argument_index"] == 2
    assert second["released_pointer_source_argument_expression"] == "released_object"
    assert report["scope"]["release_flag_role_proven"] is False
    assert report["scope"]["delete_kind_role_proven"] is False
    assert report["scope"]["ownership_semantics_proven"] is False


def test_join_fails_closed_when_release_chain_is_not_proven(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    chain = tmp_path / "release_chain.json"
    _write_argument_join(argument_join)
    _write_chain(chain, proven=False)

    report = module.join_released_pointer_role(argument_join, chain)

    assert report["backend_release_pointer_role_proven"] is False
    assert report["released_pointer_role_callsite_count"] == 0
    assert all(row["released_pointer_role_proven"] is False for row in report["rows"])
    assert all("released_pointer_wrapper_storage_not_proven" in row["missing"] for row in report["rows"])


def test_join_fails_closed_on_conflicting_wrapper_storage(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    chain = tmp_path / "release_chain.json"
    _write_argument_join(argument_join)
    _write_chain(chain, conflict=True)

    report = module.join_released_pointer_role(argument_join, chain)

    row = next(item for item in report["rows"] if item["wrapper"] == "FUN_00886950")
    assert row["released_pointer_role_proven"] is False
    assert row["released_pointer_wrapper_storage"] is None
    assert "conflicting_released_pointer_wrapper_storages" in row["missing"]


def test_join_requires_ready_source_to_wrapper_provenance(tmp_path):
    module = _load_module()
    argument_join = tmp_path / "argument_join.json"
    chain = tmp_path / "release_chain.json"
    _write_argument_join(argument_join, ready=False)
    _write_chain(chain)

    report = module.join_released_pointer_role(argument_join, chain)

    assert report["released_pointer_role_callsite_count"] == 0
    assert all("source_to_wrapper_join_not_ready" in row["missing"] for row in report["rows"])
