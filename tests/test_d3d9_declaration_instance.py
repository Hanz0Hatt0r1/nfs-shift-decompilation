import struct


def test_d3d9_declaration_instance_decodes_fields_and_type_profile():
    from d3d9_declaration_instance import decode_d3d9_declaration_records

    payload = b"".join(
        (
            struct.pack("<HHBBBB", 0, 0, 2, 0, 6, 0),
            struct.pack("<HHBBBB", 0, 12, 4, 0, 6, 1),
            struct.pack("<HHBBBB", 0, 16, 17, 0, 0, 0),
        )
    )

    result = decode_d3d9_declaration_records(payload)

    assert result["status"] == "match"
    assert result["record_stride"] == 8
    assert result["payload"]["decoded_records"] == 3
    assert result["validation"]["type_codes_recognized"] is True
    assert result["validation"]["terminator_indices"] == [2]
    assert result["records"][0]["type"] == 2
    assert result["records"][0]["type_name"] == "D3DDECLTYPE_FLOAT3"
    assert result["records"][0]["usage"] == 6
    assert result["records"][0]["usage_index"] == 0
    assert result["records"][1]["type_name"] == "D3DDECLTYPE_D3DCOLOR"
    assert result["records"][2]["type_name"] == "D3DDECLTYPE_UNUSED"
    assert result["semantic_links"]["d3dvertexelement9_shape"]["status"] == "observed"
    assert result["semantic_links"]["method_zero"]["status"] == "observed"
    assert result["meb_property_mapping"]["status"] == "not-proven"


def test_d3d9_declaration_instance_fails_closed_on_trailing_or_short_payload():
    from d3d9_declaration_instance import decode_d3d9_declaration_records

    result = decode_d3d9_declaration_records(bytes.fromhex("0000000002000600aa"))
    assert result["status"] == "partial"
    assert result["payload"]["decoded_records"] == 1
    assert result["payload"]["trailing_bytes"] == 1

    result = decode_d3d9_declaration_records(
        struct.pack("<HHBBBB", 0, 0, 2, 0, 0, 0),
        count=2,
    )
    assert result["status"] == "partial"
    assert result["payload"]["requested_records"] == 2
    assert result["payload"]["decoded_records"] == 1


def test_d3d9_declaration_instance_reports_unknown_type_and_nonzero_method():
    from d3d9_declaration_instance import decode_d3d9_declaration_records

    payload = struct.pack("<HHBBBB", 0, 0, 0xFE, 1, 6, 0)
    result = decode_d3d9_declaration_records(payload)

    assert result["status"] == "mismatch"
    assert result["records"][0]["type_status"] == "unrecognized"
    assert result["records"][0]["method_status"] == "not-proven"
    assert result["validation"]["nonzero_method_count"] == 1
    assert result["semantic_links"]["type_code_to_profile"]["status"] == "mismatch"
    assert result["semantic_links"]["method_zero"]["status"] == "not-proven"
