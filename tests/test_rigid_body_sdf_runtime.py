import rigid_body_sdf_runtime as sdf


def test_body_and_constraint_fields_match_runtime_loader():
    report = sdf.parse_sdf("""
[BODY]
name=body mass=(0.0) inertia=(1.0,2.0,3.0)
pos=(0.0,0.0,0.0) ori=(0.0,0.0,0.0)
[JOINT&HINGE]
posbody=fl_wheel negbody=fl_spindle
pos=fl_wheel axis=(-1.0,0.0,0.0)
""")
    assert report["ready"] is True
    assert report["topology"]["body_count"] == 1
    assert report["topology"]["joint_count"] == 1
    assert report["topology"]["hinge_count"] == 1
    assert report["topology"]["joint_hinge_count"] == 1
    body = sdf.records_by_type(report, "BODY")[0]
    assert body["entries"][0]["name"] == "name"
    assert body["entries"][1]["value"] == 0.0
    joint = sdf.records_by_type(report, "JOINT&HINGE")[0]
    pos = next(x for x in joint["entries"] if x["name"] == "pos")
    assert pos["value"] == "fl_wheel"
    assert pos["loader_shape"] == "tuple3-or-string"


def test_sdf_accepts_numeric_pos_and_preserves_unknown_keys():
    report = sdf.parse_sdf("""
[BAR]
name=fl_fore_lower posbody=body negbody=fl_spindle
pos=(0.1,0.2,0.3) neg=(0.4,0.5,0.6) axis=(1,0,0)
extra=keep
""")
    bar = sdf.records_by_type(report, "BAR")[0]
    assert next(x for x in bar["entries"] if x["name"] == "pos")["value"] == [0.1, 0.2, 0.3]
    extra = next(x for x in bar["entries"] if x["name"] == "extra")
    assert extra["recognized_by_loader"] is False
    assert extra["value"] == "keep"


def test_sdf_strict_mode_rejects_malformed_line():
    import pytest
    with pytest.raises(ValueError, match="unparsed"):
        sdf.parse_sdf("[BODY]\nbad line\n", strict=True)
