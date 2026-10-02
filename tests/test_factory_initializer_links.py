import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "shift_live_dump"
        / "extract_factory_initializer_links.py"
    )
    spec = importlib.util.spec_from_file_location("extract_factory_initializer_links", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "SHIFT.exe.c"
    path.write_text(
        """
void FUN_00100000(void)
{
  DAT_00c0d100 = DAT_00c0d100;
  FUN_00100100();
}

void FUN_00100100(void)
{
  DAT_00f00000 = PTR_FUN_00402100;
}

void FUN_00100200(void)
{
  DAT_00c0d100 = DAT_00c0d100;
  FUN_00100300();
}

void FUN_00100300(void)
{
  return;
}
""",
        encoding="utf-8",
    )
    return path


def _registry():
    return {
        "class_count": 2,
        "unique_vtable_count": 1,
        "classes": [
            {
                "name": "ExampleClass",
                "descriptor": 0x00C0D100,
                "descriptor_symbol": "DAT_00c0d100",
                "unique_vtable": 0x00402100,
            },
            {
                "name": "NoVtableClass",
                "descriptor": 0x00C0D200,
                "descriptor_symbol": "DAT_00c0d200",
                "unique_vtable": None,
            },
        ],
    }


def _ghidra(tmp_path: Path, include_edge: bool) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    rows = []
    if include_edge:
        rows.append(
            {
                "from_function": "0x00100000",
                "from_name": "FUN_00100000",
                "instruction": "0x00100020",
                "to": "0x00100100",
                "to_name": "FUN_00100100",
                "indirect": False,
            }
        )
    (root / "callgraph.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    return root


def test_extracts_descriptor_factory_to_unique_vtable_writer(tmp_path):
    module = _load_module()
    module.extract_registry = lambda source, exe: _registry()
    source = _source(tmp_path)
    exe = tmp_path / "SHIFT.exe"
    exe.write_bytes(b"")
    ghidra = _ghidra(tmp_path, True)

    report = module.extract_links(source, exe, ghidra)
    assert report["format"] == module.FORMAT
    assert report["linked_class_count"] == 1
    assert report["link_count"] == 1
    assert report["unambiguous_initializer_class_count"] == 1
    assert report["ghidra_confirmed_link_count"] == 1
    assert report["ghidra_mismatch_link_count"] == 0
    row = report["links"][0]
    assert row["class"] == "ExampleClass"
    assert row["factory_function"] == "FUN_00100000"
    assert row["initializer_candidate"] == "FUN_00100100"
    assert row["vtable_symbol"] == "PTR_FUN_00402100"
    assert row["ghidra_direct_call"] is True
    assert report["scope"]["constructor_semantics_proven"] is False


def test_ghidra_missing_edge_is_reported_not_silently_accepted(tmp_path):
    module = _load_module()
    module.extract_registry = lambda source, exe: _registry()
    source = _source(tmp_path)
    exe = tmp_path / "SHIFT.exe"
    exe.write_bytes(b"")
    ghidra = _ghidra(tmp_path, False)

    report = module.extract_links(source, exe, ghidra)
    assert report["link_count"] == 1
    assert report["ghidra_confirmed_link_count"] == 0
    assert report["ghidra_mismatch_link_count"] == 1
    assert report["links"][0]["ghidra_direct_call"] is False
