import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "shift_live_dump" / "build_memory_wrapper_runtime_manifest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_memory_wrapper_runtime_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _forwarding(*, release_storage=None):
    release_storage = release_storage or ["ECX:4", "DL:1", "Stack[0x4]:4"]
    return {
        "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
        "wrapper_count": 3,
        "confirmed_wrapper_forwarding_count": 3,
        "all_wrapper_forwarding_confirmed": True,
        "wrappers": [
            {
                "address": "0x008868c0",
                "name": "FUN_008868c0",
                "calling_convention": "__cdecl",
                "input_storage": ["Stack[0x4]:4"],
                "forwarding_confirmed": True,
            },
            {
                "address": "0x00886900",
                "name": "FUN_00886900",
                "calling_convention": "__cdecl",
                "input_storage": ["Stack[0x4]:4", "Stack[0x8]:4", "Stack[0xc]:4"],
                "forwarding_confirmed": True,
            },
            {
                "address": "0x00886930",
                "name": "FUN_00886930",
                "calling_convention": "__fastcall",
                "input_storage": release_storage,
                "forwarding_confirmed": True,
            },
        ],
    }


def _static_summary():
    return {
        "format": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        "static_evidence_chain_complete": True,
        "proven_physical_roles": {
            "allocation_size": {
                "proven": True,
                "function": "FUN_00638020",
                "entry_storage": "EDX:4",
            },
            "released_pointer_wrapper": {
                "proven": True,
                "wrapper_input_storage": ["Stack[0x4]:4"],
            },
        },
        "release_byte_behavior": {"analysis_complete": True},
        "scope": {"release_byte_behavior_observed": True},
    }


def _source_summary(*, release_index=2):
    return {
        "format": "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1",
        "allocation_size_role_proven": True,
        "released_pointer_role_proven": True,
        "semantic_profiles_consistent": True,
        "wrapper_profiles": [
            {
                "wrapper": "FUN_00886900",
                "allocation_size": {
                    "proven_callsite_count": 2,
                    "source_argument_index_consistent": True,
                    "source_argument_index": 0,
                    "callers": ["FUN_A"],
                    "observed_source_expressions": ["bytes"],
                },
                "released_pointer": None,
                "proven_source_roles": ["allocation-size"],
            },
            {
                "wrapper": "FUN_00886930",
                "allocation_size": None,
                "released_pointer": {
                    "proven_callsite_count": 3,
                    "source_argument_index_consistent": True,
                    "source_argument_index": release_index,
                    "callers": ["FUN_B"],
                    "observed_source_expressions": ["ptr"],
                },
                "proven_source_roles": ["released-pointer"],
            },
        ],
        "release_byte_behavior": {
            "analysis_complete": True,
            "semantic_role_assigned": False,
        },
    }


def _inputs(tmp_path, *, release_index=2, release_storage=None):
    return (
        _write(tmp_path / "forwarding.json", _forwarding(release_storage=release_storage)),
        _write(tmp_path / "static.json", _static_summary()),
        _write(tmp_path / "source.json", _source_summary(release_index=release_index)),
    )


def test_manifest_names_only_roles_admitted_by_runtime_contract(tmp_path):
    module = _load_module()
    forwarding, static, source = _inputs(tmp_path)

    report = module.build_memory_wrapper_runtime_manifest(forwarding, static, source)

    assert report["format"] == "SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1"
    assert report["runtime_contract_status"] == "source-joined-semantic-roles"
    assert report["semantic_parameter_count"] == 2
    assert report["helpers_with_proven_semantic_parameters"] == [
        "FUN_00886900",
        "FUN_00886930",
    ]

    rows = {row["name"]: row for row in report["wrappers"]}
    create = rows["FUN_00886900"]
    assert [param["name"] for param in create["parameters"]] == [
        "allocation_size",
        "arg1",
        "arg2",
    ]
    assert create["parameters"][0]["semantic_role"] == "allocation-size"
    assert create["status"] == "partial-semantic-parameters"

    release = rows["FUN_00886930"]
    assert [param["name"] for param in release["parameters"]] == [
        "arg0",
        "arg1",
        "released_pointer",
    ]
    assert release["parameters"][2]["entry_storage"] == "Stack[0x4]:4"
    assert release["parameters"][2]["semantic_role"] == "released-pointer"

    untouched = rows["FUN_008868c0"]
    assert [param["name"] for param in untouched["parameters"]] == ["arg0"]
    assert untouched["semantic_parameter_count"] == 0
    assert report["scope"]["complete_helper_abi_proven"] is False
    assert report["scope"]["calling_convention_semantics_proven"] is False
    assert report["scope"]["release_flag_role_proven"] is False


def test_manifest_fails_closed_when_proven_index_is_outside_forwarding_shape(tmp_path):
    module = _load_module()
    forwarding, static, source = _inputs(
        tmp_path,
        release_index=2,
        release_storage=["ECX:4", "DL:1"],
    )

    report = module.build_memory_wrapper_runtime_manifest(forwarding, static, source)
    release = next(row for row in report["wrappers"] if row["name"] == "FUN_00886930")

    assert [param["name"] for param in release["parameters"]] == ["arg0", "arg1"]
    assert release["semantic_parameter_count"] == 0
    assert release["blockers"] == ["semantic_source_argument_index_out_of_range"]
    assert "FUN_00886930:semantic_source_argument_index_out_of_range" in report["blockers"]


def test_manifest_does_not_promote_role_when_wrapper_forwarding_is_unconfirmed(tmp_path):
    module = _load_module()
    value = _forwarding()
    release = next(row for row in value["wrappers"] if row["name"] == "FUN_00886930")
    release["forwarding_confirmed"] = False
    forwarding = _write(tmp_path / "forwarding.json", value)
    static = _write(tmp_path / "static.json", _static_summary())
    source = _write(tmp_path / "source.json", _source_summary())

    report = module.build_memory_wrapper_runtime_manifest(forwarding, static, source)
    release_row = next(row for row in report["wrappers"] if row["name"] == "FUN_00886930")

    assert release_row["semantic_parameter_count"] == 0
    assert release_row["status"] == "forwarding-unconfirmed"
    assert release_row["blockers"] == ["wrapper_forwarding_not_confirmed"]


def test_manifest_rejects_wrong_forwarding_format(tmp_path):
    module = _load_module()
    forwarding = _write(tmp_path / "forwarding.json", {"format": "WRONG"})
    static = _write(tmp_path / "static.json", _static_summary())
    source = _write(tmp_path / "source.json", _source_summary())

    try:
        module.build_memory_wrapper_runtime_manifest(forwarding, static, source)
    except ValueError as exc:
        assert "SHIFT-MEMORY-WRAPPER-FORWARDING/1" in str(exc)
    else:
        raise AssertionError("wrong forwarding format was accepted")
