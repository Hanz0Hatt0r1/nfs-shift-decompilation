import pytest
from surface_probe_runtime import SurfaceNode, Vec3, build_contract, node_direction, probe

def test_node_direction_matches_y_cross_normal():
    assert node_direction(SurfaceNode(Vec3(0,0,0),Vec3(2,0,3),1.0,1.0)).as_tuple() == pytest.approx((0.83205029,0,-0.55470020))

def test_probe_returns_candidate_and_abs_radius():
    node=SurfaceNode(Vec3(0,0,0),Vec3(0,1,0),1.0,-2.0)
    result=probe((3.0,1.0,4.0),node)
    assert result.point.as_tuple()==pytest.approx((-2.0,0.0,0.0))
    assert result.scalar==2.0

def test_probe_recurses_to_parent_for_negative_projection():
    parent=SurfaceNode(Vec3(0,-1,0),Vec3(0,1,0),1.0,2.0)
    child=SurfaceNode(Vec3(0,1,0),Vec3(0,1,0),1.0,1.0,parent=parent)
    result=probe((0.0,0.0,0.0),child)
    assert result.used_parent and result.scalar==2.0

def test_child_same_sign_blends_candidate_and_radius():
    child=SurfaceNode(Vec3(4,0,0),Vec3(0,1,0),1.0,2.0)
    node=SurfaceNode(Vec3(0,0,0),Vec3(0,1,0),1.0,2.0,child=child)
    result=probe((0.0,1.0,0.0),node)
    assert result.point.as_tuple()==pytest.approx((6.0,0.0,0.0))
    assert result.scalar==pytest.approx(2.0)

def test_contract_freezes_offsets_and_formulas():
    c=build_contract()
    assert c["node_fields"]["point"]==["+0x8c","+0x90","+0x94"]
    assert c["node_fields"]["radius"]=="+0x158"
    assert "recurse to parent" in c["negative_projection"]
