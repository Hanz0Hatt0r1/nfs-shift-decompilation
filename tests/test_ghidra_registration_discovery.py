import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "discover_class_registrations.py"
    spec = importlib.util.spec_from_file_location("discover_class_registrations", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_discovers_registration_shape_and_crosschecks_manifest(tmp_path):
    module = _load_module()
    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "executable_md5": "abc",
                "language_id": "x86:LE:32:default",
                "image_base": "0x00400000",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"program": "SHIFT.exe"}), encoding="utf-8"
    )

    fingerprint = "a" * 64
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            {
                "address": "0x00100000",
                "name": "FUN_00100000",
                "size": 86,
                "mnemonic_sha256": fingerprint,
            },
            {
                "address": "0x00100090",
                "name": "FUN_00100090",
                "size": 120,
                "mnemonic_sha256": "b" * 64,
            },
        ],
    )

    edges = []
    for index, target in enumerate(sorted(module.REGISTRATION_CALLS)):
        edges.append(
            {
                "from_function": "0x00100000",
                "from_name": "FUN_00100000",
                "instruction": f"0x{0x00100010 + index * 4:08x}",
                "to": target,
                "to_name": "target",
                "indirect": False,
            }
        )
    # Similar looking helper that lacks _atexit must not be promoted.
    for index, target in enumerate(sorted(module.REGISTRATION_CALLS - {"0x00900fb3"})):
        edges.append(
            {
                "from_function": "0x00100090",
                "from_name": "FUN_00100090",
                "instruction": f"0x{0x001000a0 + index * 4:08x}",
                "to": target,
                "to_name": "target",
                "indirect": False,
            }
        )
    _write_jsonl(tmp_path / "callgraph.jsonl", edges)
    _write_jsonl(
        tmp_path / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00b00000",
                "value": "ExampleClass",
                "length": 13,
                "xrefs": ["0x00100004"],
                "functions": ["0x00100000"],
            },
            {
                "address": "0x00b00020",
                "value": "fieldName",
                "length": 10,
                "xrefs": ["0x00100094"],
                "functions": ["0x00100090"],
            },
        ],
    )

    class_manifest = tmp_path / "classes.json"
    class_manifest.write_text(
        json.dumps(
            {
                "format": "SHIFT-CLASS-MANIFEST/1",
                "classes": [
                    {
                        "name": "ExampleClass",
                        "registration_function": "FUN_00100000",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = module.discover(tmp_path, class_manifest)
    assert report["format"] == module.FORMAT
    assert report["candidate_count"] == 1
    assert report["single_string_candidate_count"] == 1
    candidate = report["candidates"][0]
    assert candidate["address"] == "0x00100000"
    assert candidate["single_string_name"] == "ExampleClass"
    assert candidate["mnemonic_sha256"] == fingerprint
    comparison = report["class_manifest_comparison"]
    assert comparison["verified_count"] == 1
    assert comparison["missing_candidate_count"] == 0
    assert comparison["name_mismatch_count"] == 0
    assert comparison["extra_ghidra_candidate_count"] == 0


def test_reports_name_mismatch_without_relabeling(tmp_path):
    module = _load_module()
    (tmp_path / "binary.json").write_text(json.dumps({"program_name": "SHIFT.exe"}), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"program": "SHIFT.exe"}), encoding="utf-8")
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [{"address": "0x00100000", "name": "FUN_00100000", "size": 86, "mnemonic_sha256": "c" * 64}],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            {
                "from_function": "0x00100000",
                "from_name": "FUN_00100000",
                "instruction": f"0x{0x00100010 + index * 4:08x}",
                "to": target,
                "to_name": "target",
                "indirect": False,
            }
            for index, target in enumerate(sorted(module.REGISTRATION_CALLS))
        ],
    )
    _write_jsonl(
        tmp_path / "strings_xrefs.jsonl",
        [{"address": "0x00b00000", "value": "DifferentName", "functions": ["0x00100000"], "xrefs": []}],
    )
    class_manifest = tmp_path / "classes.json"
    class_manifest.write_text(
        json.dumps(
            {
                "format": "SHIFT-CLASS-MANIFEST/1",
                "classes": [{"name": "ExpectedName", "registration_function": "FUN_00100000"}],
            }
        ),
        encoding="utf-8",
    )

    report = module.discover(tmp_path, class_manifest)
    comparison = report["class_manifest_comparison"]
    assert comparison["verified_count"] == 0
    assert comparison["name_mismatch_count"] == 1
    assert comparison["rows"][0]["ghidra_strings"] == ["DifferentName"]
    assert comparison["rows"][0]["class"] == "ExpectedName"
