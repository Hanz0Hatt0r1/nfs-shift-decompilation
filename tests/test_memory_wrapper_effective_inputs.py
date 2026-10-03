import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER_PATH = ROOT / "tools" / "ghidra" / "analyze_memory_wrapper_forwarding_retail.py"
FIXTURE_PATH = ROOT / "tests" / "test_memory_wrapper_forwarding_retail.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _wrapper(report, name):
    return next(row for row in report["wrappers"] if row["name"] == name)


def test_reports_only_inputs_observed_in_backend_arguments(tmp_path):
    driver = _load(DRIVER_PATH, "memory_wrapper_forwarding_retail_effective_inputs")
    fixture = _load(FIXTURE_PATH, "memory_wrapper_forwarding_retail_fixture")
    source = tmp_path / "memory_wrapper_instructions.jsonl"
    with source.open("w", encoding="utf-8") as handle:
        for row in fixture._retail_rows():
            handle.write(json.dumps(row) + "\n")

    report = driver.analyze_memory_wrapper_forwarding_retail(source)

    c0 = _wrapper(report, "FUN_008868c0")
    assert c0["backend_forwarded_input_storage"] == ["Stack[0x4]:4"]
    assert c0["declared_input_storage_not_forwarded_to_backend"] == []

    d0 = _wrapper(report, "FUN_008868d0")
    assert d0["backend_forwarded_input_storage"] == ["Stack[0x4]:4", "Stack[0x8]:4"]
    assert d0["declared_input_storage_not_forwarded_to_backend"] == []

    f900 = _wrapper(report, "FUN_00886900")
    assert f900["backend_forwarded_input_storage"] == [
        "Stack[0x4]:4",
        "Stack[0x8]:4",
        "Stack[0xc]:4",
    ]
    assert f900["declared_input_storage_not_forwarded_to_backend"] == []

    f930 = _wrapper(report, "FUN_00886930")
    assert f930["backend_forwarded_input_storage"] == ["DL:1", "Stack[0x4]:4"]
    assert f930["declared_input_storage_not_forwarded_to_backend"] == ["ECX:4"]

    f950 = _wrapper(report, "FUN_00886950")
    assert f950["backend_forwarded_input_storage"] == [
        "DL:1",
        "Stack[0x4]:4",
        "Stack[0x8]:4",
    ]
    assert f950["declared_input_storage_not_forwarded_to_backend"] == ["ECX:4"]

    assert report["scope"]["backend_forwarded_input_storage_instruction_derived"] is True
    assert report["scope"]["unforwarded_declared_storage_proves_unused_abi_parameter"] is False
