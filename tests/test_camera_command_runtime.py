import pytest

from camera_command_runtime import dispatch_camera_command


def test_kind_one_dispatches_to_static_view():
    result = dispatch_camera_command([99, 1, 12, 0, 7])
    assert result["operation"] == "static-view"
    assert result["arguments"] == {"group": 7, "secondary": 12}
    assert result["target_functions"] == ["FUN_0080de00"]


@pytest.mark.parametrize("kind", [2, 3])
def test_kinds_two_and_three_dispatch_to_camera_activation(kind):
    result = dispatch_camera_command([0, kind, 0, 9, 4, 5])
    assert result["operation"] == "camera-activation"
    assert result["arguments"] == {"param_3": 9, "param_1": 4, "param_2": 5}
    assert result["target_functions"] == ["FUN_0080e1b0"]


def test_kind_four_dispatches_to_external_view_source():
    result = dispatch_camera_command([12, 4])
    assert result["operation"] == "external-view-source"
    assert result["arguments"] == {"source": 12, "enabled": 1}
    assert result["target_functions"] == ["FUN_0080d520"]


def test_unknown_kind_is_explicitly_unsupported():
    result = dispatch_camera_command([0, 99])
    assert result["operation"] == "unsupported"


def test_short_command_is_rejected():
    with pytest.raises(ValueError):
        dispatch_camera_command([0])
