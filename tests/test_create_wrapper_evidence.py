import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "extract_create_wrapper_evidence.py"
        spec = importlib.util.spec_from_file_location(
            "extract_create_wrapper_evidence", path
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_recovers_immediate_helper_value_flow_and_aggregates_helpers(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        r'''
void * FUN_00100000(void)
{
    void *p;
    FUN_00700000();
    p = (void *)FUN_00886900(0x38,4);
    FUN_00110000(p);
    return p;
}

void * FUN_00100080(void)
{
    void *q;
    q = FUN_00886900(0x2c,4);
    FUN_00110100(q);
    return q;
}

void FUN_00100100(void *other)
{
    void *tmp;
    tmp = FUN_00999900(0x20);
    FUN_00110200(other);
}
''',
        encoding="utf-8",
    )

    links = tmp_path / "links.json"
    _write_json(
        links,
        {
            "format": "SHIFT-FACTORY-INITIALIZER-LINKS/1",
            "links": [
                {
                    "class": "A",
                    "descriptor": 1,
                    "factory_function": "FUN_00100000",
                    "initializer_candidate": "FUN_00110000",
                },
                {
                    "class": "B",
                    "descriptor": 2,
                    "factory_function": "FUN_00100080",
                    "initializer_candidate": "FUN_00110100",
                },
                {
                    "class": "C",
                    "descriptor": 3,
                    "factory_function": "FUN_00100100",
                    "initializer_candidate": "FUN_00110200",
                },
            ],
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    with (ghidra / "callgraph.jsonl").open("w", encoding="utf-8") as handle:
        for caller, callee in (
            ("0x00100000", "0x00886900"),
            ("0x00100000", "0x00110000"),
            ("0x00100080", "0x00886900"),
            ("0x00100080", "0x00110100"),
            ("0x00100100", "0x00999900"),
            ("0x00100100", "0x00110200"),
        ):
            handle.write(
                json.dumps(
                    {
                        "from_function": caller,
                        "to": callee,
                        "indirect": False,
                    }
                )
                + "\n"
            )

    report = module.extract_create_wrappers(source, links, ghidra)
    assert report["format"] == "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1"
    assert report["link_count"] == 3
    assert report["source_create_wrapper_shape_count"] == 2
    assert report["create_wrapper_shape_count"] == 2

    rows = {row["class_name"]: row for row in report["links"]}
    a = rows["A"]
    assert a["immediate_preinitializer_helper"] == "FUN_00886900"
    assert a["helper_assigned_local"] == "p"
    assert a["helper_result_flows_to_initializer"] is True
    assert a["helper_literal_arguments"] == [0x38, 4]
    assert a["ghidra_factory_to_helper"] is True
    assert a["ghidra_factory_to_initializer"] is True
    assert a["create_wrapper_shape"] is True

    b = rows["B"]
    assert b["helper_assigned_local"] == "q"
    assert b["helper_literal_arguments"] == [0x2C, 4]
    assert b["create_wrapper_shape"] is True

    c = rows["C"]
    assert c["immediate_preinitializer_helper"] == "FUN_00999900"
    assert c["helper_assigned_local"] == "tmp"
    assert c["helper_result_flows_to_initializer"] is False
    assert c["create_wrapper_shape"] is False

    helpers = {row["function"]: row for row in report["helpers"]}
    common = helpers["FUN_00886900"]
    assert common["linked_class_count"] == 2
    assert common["factory_count"] == 2
    assert common["result_flow_count"] == 2
    assert common["classes"] == ["A", "B"]
    assert report["scope"]["allocation_helper_semantics_proven"] is False


def test_preserves_missing_factory_and_multiple_initializer_occurrences(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        r'''
void FUN_00100000(int choose)
{
    void *a;
    void *b;
    a = FUN_00886900(0x10);
    FUN_00110000(a);
    b = FUN_00886900(0x20);
    FUN_00110000(b);
}
''',
        encoding="utf-8",
    )
    links = tmp_path / "links.json"
    _write_json(
        links,
        {
            "format": "SHIFT-FACTORY-INITIALIZER-LINKS/1",
            "links": [
                {
                    "class": "Multi",
                    "descriptor": 4,
                    "factory_function": "FUN_00100000",
                    "initializer_candidate": "FUN_00110000",
                },
                {
                    "class": "Missing",
                    "descriptor": 5,
                    "factory_function": "FUN_00900000",
                    "initializer_candidate": "FUN_00910000",
                },
            ],
        },
    )

    report = module.extract_create_wrappers(source, links)
    multi = [row for row in report["links"] if row["class_name"] == "Multi"]
    assert len(multi) == 2
    assert [row["initializer_occurrence"] for row in multi] == [0, 1]
    assert [row["helper_literal_arguments"] for row in multi] == [[0x10], [0x20]]
    assert all(row["source_create_wrapper_shape"] for row in multi)
    missing = [row for row in report["links"] if row["class_name"] == "Missing"]
    assert len(missing) == 1
    assert missing[0]["source_factory_present"] is False
    assert missing[0]["missing"] == ["factory_body"]
