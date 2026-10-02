import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_subsystem_manifests.py"
    spec = importlib.util.spec_from_file_location("build_subsystem_manifests", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_builds_promoted_aliases_and_ai_registrations(tmp_path):
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
        json.dumps({"program": "SHIFT.exe", "counts": {"functions": 99}}),
        encoding="utf-8",
    )

    function_addresses = {
        spec["address"]
        for specs in module.ALIASES.values()
        for spec in specs
    }
    function_addresses.update(address for address, _ in module.AI_REGISTRATIONS)
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            {
                "address": address,
                "name": "FUN_" + address[2:],
                "size": 86,
                "mnemonic_sha256": "f" * 64,
            }
            for address in sorted(function_addresses)
        ],
    )

    edges = []
    for specs in module.ALIASES.values():
        for spec in specs:
            for index, target in enumerate(spec["calls"]):
                edges.append(
                    {
                        "from_function": spec["address"],
                        "from_name": "alias",
                        "instruction": f"0x{index + 1:08x}",
                        "to": target,
                        "to_name": "target",
                        "indirect": False,
                    }
                )
    for address, _ in module.AI_REGISTRATIONS:
        for index, target in enumerate(sorted(module.AI_REQUIRED_CALLS)):
            edges.append(
                {
                    "from_function": address,
                    "from_name": "registry",
                    "instruction": f"0x{index + 0x100:08x}",
                    "to": target,
                    "to_name": "target",
                    "indirect": False,
                }
            )
    _write_jsonl(tmp_path / "callgraph.jsonl", edges)

    strings = []
    string_address = 0x00B00000
    for specs in module.ALIASES.values():
        for spec in specs:
            for value in spec["strings"]:
                strings.append(
                    {
                        "address": f"0x{string_address:08x}",
                        "value": value,
                        "length": len(value) + 1,
                        "xrefs": [],
                        "functions": [spec["address"]],
                    }
                )
                string_address += 4
    for address, class_name in module.AI_REGISTRATIONS:
        strings.append(
            {
                "address": f"0x{string_address:08x}",
                "value": class_name,
                "length": len(class_name) + 1,
                "xrefs": [],
                "functions": [address],
            }
        )
        string_address += 4
    _write_jsonl(tmp_path / "strings_xrefs.jsonl", strings)

    report = module.build(tmp_path)
    expected_aliases = sum(len(items) for items in module.ALIASES.values())
    assert report["format"] == module.INDEX_FORMAT
    assert len(report["semantic_aliases"]) == expected_aliases
    assert all(row["promoted"] for row in report["semantic_aliases"])
    assert all(
        row["promoted"]
        for row in report["subsystems"]["ai"]["class_registrations"]
    )
    assert report["subsystems"]["ai"]["scope"]["semantic_function_aliases_assigned"] is False

    output_dir = tmp_path / "out"
    module.write_bundle(report, output_dir)
    assert (output_dir / "index.json").is_file()
    assert (output_dir / "renderer.json").is_file()
    assert (output_dir / "physics.json").is_file()
    assert (output_dir / "vehicle.json").is_file()
    assert (output_dir / "scene_graph.json").is_file()
    assert (output_dir / "ai.json").is_file()


def test_alias_is_not_promoted_without_required_call(tmp_path):
    module = _load_module()
    (tmp_path / "binary.json").write_text(json.dumps({"program_name": "SHIFT.exe"}), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"program": "SHIFT.exe"}), encoding="utf-8")

    spec = module.ALIASES["renderer"][0]
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [{"address": spec["address"], "name": "FUN_test"}],
    )
    _write_jsonl(tmp_path / "callgraph.jsonl", [])
    _write_jsonl(
        tmp_path / "strings_xrefs.jsonl",
        [
            {
                "address": "0x00b00000",
                "value": spec["strings"][0],
                "functions": [spec["address"]],
            }
        ],
    )

    _, _, functions, outgoing, _, strings_by_function = module.build_indexes(tmp_path)
    row = module.promote_alias(spec, functions, outgoing, strings_by_function)
    assert row["checks"]["function_present"] is True
    assert all(row["checks"]["strings"].values())
    assert not all(row["checks"]["direct_calls"].values())
    assert row["promoted"] is False
