from shader_asm import OPCODES


# D3DSHADER_INSTRUCTION_OPCODE_TYPE from the Direct3D 9 SDK.  The explicit
# TEXCOORD=64 jump is intentional; values 49..63 are not D3DSIO instructions.
D3D9_OPCODES = {
    0: "NOP", 1: "MOV", 2: "ADD", 3: "SUB", 4: "MAD", 5: "MUL",
    6: "RCP", 7: "RSQ", 8: "DP3", 9: "DP4", 10: "MIN", 11: "MAX",
    12: "SLT", 13: "SGE", 14: "EXP", 15: "LOG", 16: "LIT", 17: "DST",
    18: "LRP", 19: "FRC", 20: "M4x4", 21: "M4x3", 22: "M3x4",
    23: "M3x3", 24: "M3x2", 25: "CALL", 26: "CALLNZ", 27: "LOOP",
    28: "RET", 29: "ENDLOOP", 30: "LABEL", 31: "DCL", 32: "POW",
    33: "CRS", 34: "SGN", 35: "ABS", 36: "NRM", 37: "SINCOS",
    38: "REP", 39: "ENDREP", 40: "IF", 41: "IFC", 42: "ELSE",
    43: "ENDIF", 44: "BREAK", 45: "BREAKC", 46: "MOVA", 47: "DEFB",
    48: "DEFI", 64: "TEXCOORD", 65: "TEXKILL", 66: "TEX",
    67: "TEXBEM", 68: "TEXBEML", 69: "TEXREG2AR", 70: "TEXREG2GB",
    71: "TEXM3x2PAD", 72: "TEXM3x2TEX", 73: "TEXM3x3PAD",
    74: "TEXM3x3TEX", 75: "RESERVED0", 76: "TEXM3x3SPEC",
    77: "TEXM3x3VSPEC", 78: "EXPP", 79: "LOGP", 80: "CND", 81: "DEF",
    82: "TEXREG2RGB", 83: "TEXDP3TEX", 84: "TEXM3x2DEPTH",
    85: "TEXDP3", 86: "TEXM3x3", 87: "TEXDEPTH", 88: "CMP", 89: "BEM",
    90: "DP2ADD", 91: "DSX", 92: "DSY", 93: "TEXLDD", 94: "SETP",
    95: "TEXLDL", 96: "BREAKP", 0xFFFD: "PHASE", 0xFFFE: "COMMENT",
    0xFFFF: "END",
}


def test_opcode_table_matches_d3d9_enum():
    assert OPCODES == D3D9_OPCODES


def test_reserved_gap_is_not_silently_assigned_legacy_names():
    assert all(opcode not in OPCODES for opcode in range(49, 64))


def test_high_value_shader_model_2_3_opcodes_are_not_aliases():
    assert OPCODES[66] == "TEX"
    assert OPCODES[81] == "DEF"
    assert OPCODES[91] == "DSX"
    assert OPCODES[92] == "DSY"
    assert OPCODES[93] == "TEXLDD"
    assert OPCODES[95] == "TEXLDL"
