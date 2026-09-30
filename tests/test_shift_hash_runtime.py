from shift_hash_runtime import (
    FUNCTION,
    PE_ADDRESS,
    describe_shift_hash32_runtime,
    shift_hash32,
    shift_hash32_ascii,
)


def test_fun_0063ad50_recovered_ascii_vectors():
    # Vectors generated from a literal 32-bit C transliteration of the retail
    # source/PE operation order, including wraparound after every operation.
    assert shift_hash32(b"") == 0xBD49D10D
    assert shift_hash32(b"a") == 0x29EEC818
    assert shift_hash32(b"trackdetails") == 0x0C1F0C8B
    assert shift_hash32(b"tracks\\silverstone\\era3.trd") == 0x0A1A5C1E
    assert shift_hash32(b"tracks\\brands\\brands.trd") == 0x8BE38AAA


def test_block_boundary_and_seed_vectors_are_frozen():
    assert shift_hash32(b"abcdefghijkl") == 0xF7CD38DD
    assert shift_hash32(b"abcdefghijklm") == 0x2D60A941
    assert shift_hash32(b"abc", 0x12345678) == 0x4648DCCA


def test_high_bytes_use_signed_movsx_semantics():
    assert shift_hash32(bytes((0x80, 0xFF, 0x41))) == 0xADD9BF77


def test_ascii_case_insensitive_wrapper_matches_retail_uppercase_branch():
    assert shift_hash32_ascii("abc") == 0x251E4793
    assert shift_hash32_ascii("abc", case_sensitive=False) == 0x3E36495D
    assert shift_hash32_ascii(
        "Tracks\\Silverstone\\ERA3.TRD",
        case_sensitive=False,
    ) == 0x57411A8B


def test_raw_hash_requires_bytes_and_ascii_wrapper_rejects_non_ascii():
    try:
        shift_hash32("abc")  # type: ignore[arg-type]
    except TypeError as exc:
        assert "bytes" in str(exc)
    else:
        raise AssertionError("shift_hash32 accepted text")

    try:
        shift_hash32_ascii("café")
    except UnicodeEncodeError:
        pass
    else:
        raise AssertionError("ASCII parity wrapper accepted non-ASCII input")


def test_runtime_report_records_pe_signed_byte_boundary():
    report = describe_shift_hash32_runtime()

    assert FUNCTION == "FUN_0063ad50"
    assert PE_ADDRESS == 0x0063AD50
    raw = report["case_sensitive_raw_bytes"]
    assert raw["implemented"] is True
    assert raw["byte_load"] == "signed/movsx"
    assert raw["four_byte_order"] == "big-endian accumulation"
    assert raw["block_size"] == 12
    assert raw["word_size_bits"] == 32
    assert report["case_insensitive_text"]["non_ascii_locale_parity"] is False
