import json
from pathlib import Path


def test_shift_exe_102_static_d3d9_tables():
    path = Path("tests/fixtures/shift_exe_102_d3d9_tables.json")
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["format"] == "SHIFT.D3D9ExecutableEvidence/1"
    assert report["source"]["machine"] == "0x014c"
    assert report["source"]["image_base"] == "0x00400000"

    assert report["tables"]["type_code"]["values"][:17] == list(range(17))
    assert report["tables"]["type_size"]["values"][:17] == [4,8,12,16,4,4,4,8,4,4,8,4,8,4,4,4,8]
    assert report["tables"]["type_components"]["values"][:17] == [1,2,3,4,4,4,2,4,4,2,4,2,4,3,3,2,4]

    assert report["type_names"][4] == "RGBA32"
    assert report["semantic_observations"]["type_4"]["d3d9_type"] == "D3DDECLTYPE_D3DCOLOR"

    usage = report["tables"]["usage"]["values"]
    assert usage[6] == 10
    assert report["semantic_observations"]["usage_6"]["source_name"] == "Colour"

    assert report["semantic_observations"]["meb_color_descriptors"] == {
        "460": [4,6,0],
        "461": [4,6,1],
    }
