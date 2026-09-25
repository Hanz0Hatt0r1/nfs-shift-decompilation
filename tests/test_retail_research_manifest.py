from retail_research_manifest import build_retail_research_manifest


def test_retail_manifest_fingerprints_and_compares_expected_hash(tmp_path):
    path = tmp_path / "SHIFT.exe"
    path.write_bytes(b"retail")
    import hashlib
    expected = hashlib.sha256(b"retail").hexdigest()

    report = build_retail_research_manifest(
        [path],
        expected_sha256={"SHIFT.exe": expected},
    )
    assert report["ready"] is True
    assert report["artifacts"][0]["sha256_status"] == "match"


def test_retail_manifest_blocks_hash_mismatch(tmp_path):
    path = tmp_path / "SHIFT.exe"
    path.write_bytes(b"retail")
    report = build_retail_research_manifest(
        [path],
        expected_sha256={"SHIFT.exe": "0" * 64},
    )
    assert report["ready"] is False
    assert "retail-manifest:sha256-mismatch:SHIFT.exe" in report["blocking_reasons"]


def test_retail_manifest_blocks_missing_file(tmp_path):
    path = tmp_path / "BMW_M3_E36.bff"
    report = build_retail_research_manifest([path])
    assert report["ready"] is False
    assert "retail-manifest:file-missing" in report["blocking_reasons"][0]


def test_retail_manifest_does_not_commit_binary_content(tmp_path):
    path = tmp_path / "RENDER.bff"
    path.write_bytes(b"archive")
    report = build_retail_research_manifest([path])
    assert report["policy"]["identity_only"] is True
    assert "data" not in report["artifacts"][0]
