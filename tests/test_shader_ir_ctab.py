import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shader_ir import _parse_ctab


def test_ctab_decodes_constant_register_and_type():
    data = bytearray(160)
    data[0:4] = b"CTAB"

    header = struct.pack(
        "<7I",
        96,      # size
        0,       # creator
        0x300,   # version
        1,       # constants
        32,      # constant info offset, relative to CTAB payload
        0,       # flags
        0,       # target
    )
    data[4:32] = header

    # ConstantInfo at payload+32.
    data[32:52] = struct.pack(
        "<IHHHHII",
        52,      # name offset
        2,       # register set: float4
        7,       # c7
        1,       # register count
        0,
        72,      # type info
        0,       # default value
    )

    # TypeInfo at payload+72.
    data[72:88] = struct.pack(
        "<BBHHHHI",
        1,       # class: vector
        3,       # type: float
        1, 4, 1, 0, 0,
    )
    data[52:59] = b"Diffuse\\x00"

    ctab = _parse_ctab(bytes(data), 0, 24)
    assert ctab["constant_count"] == 1
    c = ctab["constants"][0]
    assert c["name"] == "Diffuse"
    assert c["register_set"] == 2
    assert c["register_index"] == 7
    assert c["register_count"] == 1
    assert c["type"]["rows"] == 1
    assert c["type"]["columns"] == 4


def test_ctab_keeps_strings_for_legacy_variants():
    data = bytearray(96)
    data[0:4] = b"CTAB"
    data[4:32] = struct.pack("<7I", 32, 0, 0x300, 0, 0, 0, 0)
    data[40:47] = b"legacy\\x00"
    ctab = _parse_ctab(bytes(data), 0, 16)
    assert "legacy" in ctab["strings"]
