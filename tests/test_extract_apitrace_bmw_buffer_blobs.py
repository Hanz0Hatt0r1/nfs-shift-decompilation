import json

import tools.extract_apitrace_bmw_buffer_blobs as mod


def uvarint(value: int) -> bytes:
    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            out.append(chunk | 0x80)
        else:
            out.append(chunk)
            return bytes(out)


def string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return uvarint(len(raw)) + raw


def opaque(value: int) -> bytes:
    return bytes([mod.TYPE_OPAQUE]) + uvarint(value)


def uint(value: int) -> bytes:
    return bytes([mod.TYPE_UINT]) + uvarint(value)


def blob(value: bytes) -> bytes:
    return bytes([mod.TYPE_BLOB]) + uvarint(len(value)) + value


def call_enter(
    call_no: int,
    sig_id: int,
    name: str,
    arg_names: list[str],
    args: dict[int, bytes],
    *,
    fake: bool = False,
) -> bytes:
    del call_no
    out = bytearray([mod.EVENT_ENTER, 0])
    out += uvarint(sig_id)
    out += string(name)
    out += uvarint(len(arg_names))
    for arg_name in arg_names:
        out += string(arg_name)
    for index, value in sorted(args.items()):
        out += bytes([mod.CALL_ARG]) + uvarint(index) + value
    if fake:
        out += bytes([mod.CALL_FLAGS]) + uvarint(mod.FLAG_FAKE)
    out.append(mod.CALL_END)
    return bytes(out)


def leave(call_no: int) -> bytes:
    return bytes([mod.EVENT_LEAVE]) + uvarint(call_no) + bytes([mod.CALL_END])


def synthetic_trace() -> bytes:
    out = bytearray()
    out += uvarint(mod.TRACE_VERSION)
    out += uvarint(mod.TRACE_VERSION)
    out += uvarint(0)

    # apitrace emits the fake memcpy immediately before the real Unlock.
    out += call_enter(
        0,
        1,
        "memcpy",
        ["dest", "src", "n"],
        {0: opaque(0x200), 1: blob(b"ABCDEFGH"), 2: uint(8)},
        fake=True,
    )
    out += leave(0)

    out += call_enter(
        1,
        2,
        "IDirect3DVertexBuffer9::Unlock",
        ["this"],
        {0: opaque(0x100)},
    )
    out += leave(1)
    return bytes(out)


def geometry_report(tmp_path):
    path = tmp_path / "geometry.json"
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
                "resources": {
                    "vertex_buffers": [
                        {
                            "pointer": "0x100",
                            "creation": {
                                "call": 99,
                                "raw": (
                                    "99 IDirect3DDevice9::CreateVertexBuffer("
                                    "Length = 8) = D3D_OK"
                                ),
                            },
                            "lifecycle": {
                                "lock_calls": [],
                                "unlock_calls": [1],
                                "release_calls": [],
                            },
                            "derived_bytes_if_num_vertices_times_stride": 8,
                        }
                    ],
                    "index_buffers": [],
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_extracts_fake_memcpy_type_blob(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mod,
        "read_trace_bytes",
        lambda trace, limit: synthetic_trace(),
    )
    report = geometry_report(tmp_path)
    out = tmp_path / "out"

    summary = mod.extract(
        tmp_path / "bmw_buffer_payload.trace",
        report,
        out,
    )

    assert summary["payload_records"] == 1
    assert summary["unique_payload_blobs"] == 1
    assert summary["full_buffer_candidates"] == 1

    payloads = list((out / "buffer_payloads").glob("*.bin"))
    assert len(payloads) == 1
    assert payloads[0].read_bytes() == b"ABCDEFGH"

    evidence = json.loads(
        (out / "buffer_blob_evidence.json").read_text(encoding="utf-8")
    )
    row = evidence["buffers"][0]
    assert row["buffer_pointer"] == "0x100"
    assert row["unlock_call"] == 1
    assert row["fake_memcpy_call"] == 0
    assert row["blob_size"] == 8
    assert row["n_matches_blob_size"] is True
    assert row["full_buffer_candidate"] is True


def test_invalid_trace_magic_is_rejected(tmp_path):
    path = tmp_path / "bad.trace"
    path.write_bytes(b"not-an-apitrace")
    try:
        mod.read_trace_bytes(path, 1024)
    except mod.TraceFormatError as exc:
        assert "Snappy trace" in str(exc)
    else:
        raise AssertionError("invalid trace was accepted")
