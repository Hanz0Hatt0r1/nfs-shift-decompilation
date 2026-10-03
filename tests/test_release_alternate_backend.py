import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_release_alternate_backend.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_release_alternate_backend", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value):
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _release_chain(*, proven=True, storage="Stack[0x4]:4"):
    return {
        "format": "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1",
        "release_pointer_to_wrapper_storage_proven": proven,
        "wrapper_paths": [
            {
                "wrapper": "FUN_00886930",
                "wrapper_address": "0x00886930",
                "wrapper_input_storage": "Stack[0x4]:4",
                "released_pointer_path_proven": True,
            },
            {
                "wrapper": "FUN_00886950",
                "wrapper_address": "0x00886950",
                "wrapper_input_storage": storage,
                "released_pointer_path_proven": proven,
            },
        ],
    }


def _forwarding(
    *,
    pointer_source="input:Stack[0x4]:4",
    other_source="input:Stack[0x8]:4",
    confirmed=True,
):
    return {
        "format": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
        "wrappers": [
            {
                "address": "0x00886950",
                "name": "FUN_00886950",
                "forwarding_confirmed": confirmed,
                "call_sites": [
                    {
                        "instruction": "0x00886966",
                        "target": "0x0064f260",
                        "transfer_kind": "tail-call",
                        "arguments": [
                            {
                                "storage": "ECX:4",
                                "source": other_source,
                                "resolved": True,
                            },
                            {
                                "storage": "EDX:4",
                                "source": pointer_source,
                                "resolved": True,
                            },
                        ],
                    },
                    {
                        "instruction": "0x0088696c",
                        "target": "0x0064f4c0",
                        "transfer_kind": "tail-call",
                        "arguments": [
                            {
                                "storage": "ECX:4",
                                "source": "input:Stack[0x4]:4",
                                "resolved": True,
                            },
                            {
                                "storage": "DL:1",
                                "source": "input:DL:1",
                                "resolved": True,
                            },
                        ],
                    },
                ],
            }
        ],
    }


def test_alternate_branch_promotes_same_proven_wrapper_pointer_to_edx(tmp_path):
    module = _load_module()
    release_chain = tmp_path / "release_chain.json"
    forwarding = tmp_path / "forwarding.json"
    _write(release_chain, _release_chain())
    _write(forwarding, _forwarding())

    report = module.analyze_release_alternate_backend(release_chain, forwarding)

    assert report["wrapper"] == "FUN_00886950"
    assert report["alternate_backend"] == "0x0064f260"
    assert report["proven_released_pointer_wrapper_storage"] == "Stack[0x4]:4"
    assert report["alternate_site_count"] == 1
    assert report["released_pointer_to_alternate_backend_storage_proven"] is True
    assert report["alternate_backend_released_pointer_entry_storage"] == "EDX:4"
    assert report["other_alternate_backend_entry_storage"] == ["ECX:4"]
    assert report["blockers"] == []
    site = report["alternate_sites"][0]
    assert site["site_proven"] is True
    assert site["released_pointer_backend_storage"] == "EDX:4"
    assert site["arguments"][0]["same_as_proven_released_pointer"] is False
    assert site["arguments"][1]["same_as_proven_released_pointer"] is True
    scope = report["scope"]
    assert scope["alternate_backend_released_pointer_role_proven"] is True
    assert scope["alternate_backend_function_semantics_proven"] is False
    assert scope["other_alternate_backend_argument_roles_proven"] is False
    assert scope["release_flag_role_proven"] is False
    assert scope["ownership_semantics_proven"] is False


def test_alternate_branch_fails_closed_without_diagnostic_backed_wrapper_role(tmp_path):
    module = _load_module()
    release_chain = tmp_path / "release_chain.json"
    forwarding = tmp_path / "forwarding.json"
    _write(release_chain, _release_chain(proven=False))
    _write(forwarding, _forwarding())

    report = module.analyze_release_alternate_backend(release_chain, forwarding)

    assert report["released_pointer_to_alternate_backend_storage_proven"] is False
    assert report["alternate_backend_released_pointer_entry_storage"] is None
    assert "release_pointer_chain_not_proven" in report["blockers"]


def test_alternate_branch_fails_when_forwarding_uses_different_wrapper_input(tmp_path):
    module = _load_module()
    release_chain = tmp_path / "release_chain.json"
    forwarding = tmp_path / "forwarding.json"
    _write(release_chain, _release_chain())
    _write(
        forwarding,
        _forwarding(
            pointer_source="input:Stack[0x8]:4",
            other_source="input:Stack[0xc]:4",
        ),
    )

    report = module.analyze_release_alternate_backend(release_chain, forwarding)

    assert report["released_pointer_to_alternate_backend_storage_proven"] is False
    assert report["alternate_backend_released_pointer_entry_storage"] is None
    assert report["blockers"] == ["alternate_backend_pointer_match_not_unique"]


def test_alternate_branch_fails_when_wrapper_forwarding_is_unconfirmed(tmp_path):
    module = _load_module()
    release_chain = tmp_path / "release_chain.json"
    forwarding = tmp_path / "forwarding.json"
    _write(release_chain, _release_chain())
    _write(forwarding, _forwarding(confirmed=False))

    report = module.analyze_release_alternate_backend(release_chain, forwarding)

    assert report["alternate_site_count"] == 0
    assert report["released_pointer_to_alternate_backend_storage_proven"] is False
    assert report["blockers"] == ["alternate_wrapper_forwarding_not_confirmed"]


def test_alternate_branch_rejects_wrong_input_formats(tmp_path):
    module = _load_module()
    release_chain = tmp_path / "release_chain.json"
    forwarding = tmp_path / "forwarding.json"
    _write(release_chain, {"format": "WRONG"})
    _write(forwarding, _forwarding())

    try:
        module.analyze_release_alternate_backend(release_chain, forwarding)
    except ValueError as exc:
        assert "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1" in str(exc)
    else:
        raise AssertionError("wrong release-chain format must fail")
