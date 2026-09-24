from runtime_texture_reference import ppms_to_reference_cube, ppm_to_reference_texture


def _ppm(width, height, pixels):
    header = f"P6\n{width} {height}\n255\n".encode()
    return header + bytes(pixels)


def test_ppm_becomes_reference_texture(tmp_path):
    path = tmp_path / "a.ppm"
    path.write_bytes(_ppm(2, 1, [255, 0, 1, 2, 3, 4]))
    result = ppm_to_reference_texture(path)
    assert result["format"] == "SHIFT.ReferenceTexture/1"
    assert result["width"] == 2
    assert result["height"] == 1
    assert result["pixels"] == [255, 0, 1, 255, 2, 3, 4, 255]


def test_six_ppms_become_reference_cube(tmp_path):
    paths = {}
    for face in ("px", "nx", "py", "ny", "pz", "nz"):
        path = tmp_path / f"{face}.ppm"
        path.write_bytes(_ppm(1, 1, [10, 20, 30]))
        paths[face] = path

    result = ppms_to_reference_cube(paths)
    assert result["format"] == "SHIFT.ReferenceCubeTexture/1"
    assert set(result["faces"]) == {"px", "nx", "py", "ny", "pz", "nz"}
    assert all(face["width"] == 1 and face["height"] == 1 for face in result["faces"].values())
