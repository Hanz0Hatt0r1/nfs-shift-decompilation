import resource_content_index as runtime


def test_content_index_separates_path_and_payload_identity():
    result = runtime.build_resource_content_index(
        [
            {
                "archive": "A.bff",
                "path": r"render\shaders\common.fxo",
                "raw_sha256": "AA",
                "type": 2,
                "compressed_size": 10,
                "uncompressed_size": 20,
            },
            {
                "archive": "B.bff",
                "path": "render/shaders/common.fxo",
                "raw_sha256": "aa",
                "type": 2,
                "compressed_size": 10,
                "uncompressed_size": 20,
            },
            {
                "archive": "C.bff",
                "path": "render/shaders/other.fxo",
                "raw_sha256": "bb",
            },
        ]
    )

    assert result["unique_paths"] == 2
    assert result["unique_sha256"] == 2
    assert result["path_groups"][0]["occurrences"] == 2
    assert result["path_groups"][0]["sha256_values"] == ["aa"]


def test_find_exact_payload_matches_is_case_insensitive():
    index = runtime.build_resource_content_index(
        [
            {"archive": "A.bff", "path": "x.dds", "raw_sha256": "abc"},
            {"archive": "B.bff", "path": "y.dds", "raw_sha256": "abc"},
        ]
    )
    matches = runtime.find_exact_payload_matches(index, "ABC")
    assert len(matches) == 1
    assert matches[0]["occurrences"] == 2
    assert matches[0]["archives"] == ["A.bff", "B.bff"]
