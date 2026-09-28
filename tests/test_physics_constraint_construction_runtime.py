import physics_constraint_construction_runtime as runtime


def _report():
    records = []
    bodies = ["body", "fl_spindle", "fr_spindle", "fl_wheel", "fr_wheel", "rl_spindle", "rr_spindle", "rl_wheel", "rr_wheel", "fuel_tank", "driver_head"]
    for name in bodies:
        records.append({"section":"BODY","entries":[
            {"name":"name","value":name},
            {"name":"mass","value":1.0},
            {"name":"inertia","value":[1.0,1.0,1.0]},
        ]})
    pairs=[("fl_wheel","fl_spindle"),("fr_wheel","fr_spindle"),("rl_wheel","rl_spindle"),("rr_wheel","rr_spindle")]
    for a,b in pairs[:2]:
        records.append({"section":"JOINT&HINGE","entries":[
            {"name":"posbody","value":a},{"name":"negbody","value":b},{"name":"pos","value":a},
            {"name":"axis","value":[1.0,0.0,0.0]},{"name":"neg","value":[0.0,1.0,0.0]}
        ]})
    for i, target in enumerate(["fl_spindle"]*5+["fr_spindle"]*5+["rl_spindle"]*5+["rr_spindle"]*5):
        records.append({"section":"BAR","entries":[
            {"name":"name","value":f"bar_{i}"},{"name":"posbody","value":"body"},{"name":"negbody","value":target},
            {"name":"pos","value":[0.0,0.0,0.0]},{"name":"neg","value":[1.0,0.0,0.0]}
        ]})
    for a,b in pairs[2:]:
        records.append({"section":"JOINT&HINGE","entries":[
            {"name":"posbody","value":a},{"name":"negbody","value":b},{"name":"pos","value":a},
            {"name":"axis","value":[1.0,0.0,0.0]},{"name":"neg","value":[0.0,1.0,0.0]}
        ]})
    return {"records":records}


def test_real_bmw_shape_is_28_records_and_40_scalars():
    plan=runtime.build_prephysx_construction_plan(_report())
    assert plan["ready"]
    assert plan["counts"]=={"bodies":11,"joint":4,"hinge":4,"bar":20,"runtime_constraints":28,"solver_scalar_count":40}
    assert plan["allocations"]["body_runtime_bytes"]==11*0x170
    assert plan["allocations"]["matrix_bytes"]==40*40*8


def test_joint_hinge_materializes_in_source_order():
    plan=runtime.build_prephysx_construction_plan(_report())
    rows=plan["constraints"]["rows"]
    assert [(r["runtime_section"],r["source_record_index"]) for r in rows[:4]]==[
        ("JOINT",11),("HINGE",11),("JOINT",12),("HINGE",12)
    ]


def test_body_offsets_match_exact_helper_contract():
    body=runtime.build_prephysx_construction_plan(_report())["body"]
    ops=body["rows"][0]["operations"]
    assert ops[0]["source"]=="+0x20"
    assert ops[0]["destination"]=="+0x100"
    assert ops[2]["destination"]=="+0x90"
    assert ops[4]["destination"]==["+0x138","+0x140","+0x148"]


def test_missing_body_reference_blocks_plan():
    report=_report()
    report["records"].append({"section":"BAR","entries":[
        {"name":"posbody","value":"body"},{"name":"negbody","value":"missing"}
    ]})
    plan=runtime.build_prephysx_construction_plan(report)
    assert plan["ready"] is False
    assert "record:35:negbody:missing" in plan["errors"]


def test_expected_shape_validator():
    plan=runtime.build_prephysx_construction_plan(_report())
    result=runtime.validate_expected_shape(plan, body_count=11, joint_hinge_count=4, bar_count=20)
    assert result["ready"]
    assert result["errors"]==[]
