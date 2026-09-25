import pytest

from camera_view_default_runtime import camera_view_default_state


def test_projection_defaults_match_initializer_bits():
    fields = camera_view_default_state()["fields"]
    assert fields["FOV"]["default"]["bits_hex"] == "0x3f490fdb"
    assert fields["AspectRatio"]["default"]["bits_hex"] == "0x3faaaaab"
    assert fields["NearZ"]["default"]["bits_hex"] == "0x3dcccccd"
    assert fields["FarZ"]["default"]["bits_hex"] == "0x443b8000"


def test_projection_defaults_decode_to_expected_scalars():
    fields = camera_view_default_state()["fields"]
    assert fields["FOV"]["default"]["value"] == pytest.approx(0.7853981852531433)
    assert fields["AspectRatio"]["default"]["value"] == pytest.approx(1.3333333730697632)
    assert fields["NearZ"]["default"]["value"] == pytest.approx(0.1)
    assert fields["FarZ"]["default"]["value"] == pytest.approx(750.0)


def test_storage_offsets_are_the_registered_offsets():
    fields = camera_view_default_state()["fields"]
    assert fields["FOV"]["offset"] == 0x34
    assert fields["AspectRatio"]["offset"] == 0x38
    assert fields["NearZ"]["offset"] == 0x3C
    assert fields["FarZ"]["offset"] == 0x40