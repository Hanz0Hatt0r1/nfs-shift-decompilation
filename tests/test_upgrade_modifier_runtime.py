import pytest

from upgrade_modifier_runtime import ModifierNode, describe_modifier_chain, evaluate_modifier_chain


def test_modifier_chain_multiplies_and_adds_in_source_order():
    nodes = (
        ModifierNode(1.0, 2.0, 0, 4, additive=False, next_index=1),
        ModifierNode(5.0, 9.0, 0, 4, additive=True, next_index=None),
    )
    report = evaluate_modifier_chain(10.0, 2, nodes)
    # node0 -> 1.5, node1 -> 7.0: 10*1.5 + 7 = 22
    assert report["product"] == pytest.approx(1.5)
    assert report["additive"] == pytest.approx(7.0)
    assert report["result"] == pytest.approx(22.0)
    assert [row["node_index"] for row in report["matched_nodes"]] == [0, 1]


def test_modifier_chain_uses_constant_endpoint_when_level_span_is_zero():
    nodes = (ModifierNode(1.25, 9.0, 3, 3, additive=False),)
    report = evaluate_modifier_chain(8.0, 3, nodes)
    assert report["matched_nodes"][0]["interpolated_value"] == pytest.approx(1.25)
    assert report["result"] == pytest.approx(10.0)


def test_modifier_chain_skips_nodes_outside_level_interval():
    nodes = (
        ModifierNode(2.0, 4.0, 0, 1, additive=False, next_index=1),
        ModifierNode(10.0, 14.0, 3, 5, additive=True),
    )
    report = evaluate_modifier_chain(5.0, 2, nodes)
    assert report["matched_nodes"] == []
    assert report["product"] == 1.0
    assert report["additive"] == 0.0
    assert report["result"] == 5.0


def test_modifier_chain_rejects_cycles_and_bad_links():
    with pytest.raises(ValueError, match="cycle"):
        evaluate_modifier_chain(
            1.0,
            0,
            (ModifierNode(1.0, 1.0, 0, 0, next_index=0),),
        )
    with pytest.raises(ValueError, match="out of range"):
        evaluate_modifier_chain(
            1.0,
            0,
            (ModifierNode(1.0, 1.0, 0, 0, next_index=2),),
        )


def test_modifier_chain_descriptor_exposes_0x18_node_stride():
    report = describe_modifier_chain((
        ModifierNode(1.0, 2.0, 0, 1),
        ModifierNode(3.0, 4.0, 2, 3),
    ))
    assert report["record_stride"] == 0x18
    assert report["nodes"][0]["next_index"] is None
    assert report["evidence"]["function"] == "FUN_007a6be0"
