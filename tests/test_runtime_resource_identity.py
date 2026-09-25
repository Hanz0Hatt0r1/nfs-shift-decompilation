from runtime_resource_identity import match_resource_identity


def test_resource_identity_exact_sha_match_is_case_insensitive():
    matched, status = match_resource_identity(
        {
            "resource_sha256": " AbCd ",
            "resource_path": r"vehicles\bmw\body.meb",
        },
        expected_sha256="abcd",
        expected_path="vehicles/bmw/body.meb",
    )
    assert matched is True
    assert status == "exact-sha-match"


def test_resource_identity_never_downgrades_missing_sha_to_path():
    matched, status = match_resource_identity(
        {"resource_path": "vehicles/bmw/body.meb"},
        expected_sha256="abcd",
        expected_path="vehicles/bmw/body.meb",
    )
    assert matched is False
    assert status == "path-match-sha-missing"


def test_resource_identity_reports_sha_mismatch():
    matched, status = match_resource_identity(
        {"resource_sha256": "other"},
        expected_sha256="abcd",
        expected_path="vehicles/bmw/body.meb",
    )
    assert matched is False
    assert status == "sha-mismatch"


def test_resource_identity_supports_explicit_path_only_mode():
    matched, status = match_resource_identity(
        {"resource_path": r"VEHICLES\BMW\BODY.MEB"},
        expected_path="vehicles/bmw/body.meb",
    )
    assert matched is True
    assert status == "path-match"


def test_resource_identity_reports_missing_binding():
    matched, status = match_resource_identity(
        {},
        expected_path="vehicles/bmw/body.meb",
    )
    assert matched is False
    assert status == "path-missing"
