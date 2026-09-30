from shift_importer import classify, dependency_hints


def test_imb_and_imx_are_mesh_instance_resources():
    assert classify("tracks/test/banner.imb") == "MESH_INSTANCE"
    assert classify(r"tracks\test\instance.IMX") == "MESH_INSTANCE"


def test_dependency_hints_recognize_imx_paths():
    data = b'"tracks/test/instance.imx"'
    assert dependency_hints(data, "tracks/test/source.xml") == [
        "tracks/test/instance.imx"
    ]
