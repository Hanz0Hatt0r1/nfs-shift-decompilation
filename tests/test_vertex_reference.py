import pytest

from vertex_reference import build_vertex_inputs, execute_vertex, execute_vertex_program


def _operand(kind, reg_type, index, *, swizzle="xyzw", write_mask=None):
    return {
        "token": 0x80000000,
        "kind": kind,
        "reg_type": reg_type,
        "index": index,
        "swizzle": swizzle,
        "source_modifier": 0,
        "write_mask": write_mask,
    }


def _program():
    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": "vertex",
        "shader_model": [3, 0],
        "offset": 0,
        "end": 0,
        "inputs": [
            {"usage": "POSITION", "index": 0, "register": "v0"},
            {"usage": "TEXCOORD", "index": 0, "register": "v1"},
        ],
        "outputs": [
            {"usage": "POSITION", "index": 0, "register": "oR0"},
            {"usage": "TEXCOORD", "index": 0, "register": "oT0"},
        ],
        "samplers": [],
        "constants": [],
        "temps": [],
        "unsupported_opcodes": [],
        "instructions": [
            {
                "offset": 0,
                "opcode": 1,
                "name": "MOV",
                "token": 0,
                "length": 3,
                "controls": 0,
                "predicated": False,
                "operands": [
                    _operand("dest", 4, 0, write_mask="xyzw"),
                    _operand("source", 1, 0),
                ],
                "predicate": None,
            },
            {
                "offset": 12,
                "opcode": 1,
                "name": "MOV",
                "token": 0,
                "length": 3,
                "controls": 0,
                "predicated": False,
                "operands": [
                    _operand("dest", 6, 0, write_mask="xyzw"),
                    _operand("source", 1, 1),
                ],
                "predicate": None,
            },
        ],
        "const_ints": [],
        "const_bools": [],
        "sampler_types": {},
    }


def _mesh():
    return {
        "vertices": [
            (1.0, 2.0, 3.0),
            (4.0, 5.0, 6.0),
        ],
        "uv_layers": {
            "130": [(0.1, 0.2), (0.3, 0.4)],
        },
    }


def test_build_vertex_inputs_maps_position_and_texcoord0():
    assert build_vertex_inputs(_program(), _mesh(), 1) == {
        0: (4.0, 5.0, 6.0, 1.0),
        1: (0.3, 0.4, 0.0, 1.0),
    }


def test_execute_vertex_keeps_typed_oR0_and_oT0_outputs_separate():
    result = execute_vertex(_program(), _mesh(), 0)
    assert result["status"] == "executed"
    assert result["position_clip"] == [1.0, 2.0, 3.0, 1.0]
    assert result["outputs"]["POSITION0"] == [1.0, 2.0, 3.0, 1.0]
    assert result["outputs"]["TEXCOORD0"] == [0.1, 0.2, 0.0, 1.0]
    assert result["shader_execution"]["output_registers"]["4:0"] == [1.0, 2.0, 3.0, 1.0]
    assert result["shader_execution"]["output_registers"]["6:0"] == [0.1, 0.2, 0.0, 1.0]


def test_execute_vertex_program_runs_all_vertices():
    result = execute_vertex_program(_program(), _mesh())
    assert result["status"] == "executed"
    assert result["vertex_count"] == 2
    assert result["vertices"][1]["position_clip"] == [4.0, 5.0, 6.0, 1.0]


def test_execute_vertex_reports_missing_attribute():
    mesh = _mesh()
    mesh["uv_layers"] = {}
    result = execute_vertex(_program(), mesh, 0)
    assert result["status"] == "error"
    assert "requires TEXCOORD0" in result["blocking_reasons"][0]


def test_execute_vertex_rejects_pixel_program():
    program = dict(_program())
    program["stage"] = "pixel"
    result = execute_vertex(program, _mesh(), 0)
    assert result["status"] == "unsupported"
    assert "vertex-program:not-vertex-stage" in result["blocking_reasons"]
