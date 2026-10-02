import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "analyze_shift_export.py"
    spec = importlib.util.spec_from_file_location("analyze_shift_export", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_analyze_crosschecks_direct_layers(tmp_path):
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
        json.dumps({"program": "SHIFT.exe", "counts": {"functions": 9}}),
        encoding="utf-8",
    )

    fingerprint = "f" * 64
    functions = []
    for key, anchor in module.ANCHORS.items():
        functions.append(
            {
                "address": anchor["address"],
                "name": "FUN_" + anchor["address"][2:],
                "size": 10,
                "mnemonic_sha256": key,
            }
        )
    for address in module.REGISTRY_SEEDS:
        functions.append(
            {
                "address": address,
                "name": "FUN_" + address[2:],
                "size": 86,
                "mnemonic_sha256": fingerprint,
            }
        )
    _write_jsonl(tmp_path / "functions.jsonl", functions)

    edges = []
    for anchor in module.ANCHORS.values():
        for index, target in enumerate(anchor["expected_calls"]):
            edges.append(
                {
                    "from_function": anchor["address"],
                    "from_name": "anchor",
                    "instruction": f"0x{index + 1:08x}",
                    "to": target,
                    "to_name": "target",
                    "indirect": False,
                }
            )
    for seed in module.REGISTRY_SEEDS:
        for index, target in enumerate(sorted(module.REGISTRY_REQUIRED_CALLS)):
            edges.append(
                {
                    "from_function": seed,
                    "from_name": "registry",
                    "instruction": f"0x{index + 0x100:08x}",
                    "to": target,
                    "to_name": "target",
                    "indirect": False,
                }
            )
    _write_jsonl(tmp_path / "callgraph.jsonl", edges)

    strings = []
    for anchor in module.ANCHORS.values():
        for index, value in enumerate(anchor["expected_strings"]):
            strings.append(
                {
                    "address": f"0x{index + 0x00B00000:08x}",
                    "value": value,
                    "length": len(value) + 1,
                    "xrefs": [],
                    "functions": [anchor["address"]],
                }
            )
    for index, seed in enumerate(module.REGISTRY_SEEDS):
        strings.append(
            {
                "address": f"0x{index + 0x00B10000:08x}",
                "value": f"Class{index}",
                "length": 7,
                "xrefs": [],
                "functions": [seed],
            }
        )
    _write_jsonl(tmp_path / "strings_xrefs.jsonl", strings)

    report = module.analyze(tmp_path)
    assert report["format"] == module.FORMAT
    assert report["source"]["program"] == "SHIFT.exe"
    assert report["scope"]["heuristic_vtables_used"] is False
    assert all(anchor["checks"]["function_present"] for anchor in report["anchors"])
    assert all(all(anchor["checks"]["expected_strings"].values()) for anchor in report["anchors"])
    assert all(all(anchor["checks"]["expected_calls"].values()) for anchor in report["anchors"])
    assert report["rtti_registration_fingerprint"]["matching_function_count"] == 4
    assert report["rtti_registration_fingerprint"]["registration_shape_match_count"] == 4
