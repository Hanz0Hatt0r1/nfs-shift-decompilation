import struct

from spirv_reflection import reflect_spirv


def _inst(opcode, operands):
    return [((1 + len(operands)) << 16) | opcode, *operands]


def _string_words(value):
    raw = value.encode("utf-8") + b"\0"
    raw += b"\0" * ((4 - len(raw) % 4) % 4)
    return list(struct.unpack("<" + "I" * (len(raw) // 4), raw))


def _module(instructions, bound=64):
    words = [0x07230203, 0x00010500, 0, bound, 0]
    for inst in instructions:
        words.extend(_inst(inst[0], inst[1]))
    return struct.pack("<" + "I" * len(words), *words)


def _cube_module():
    return _module([
        (5, [10, *_string_words("tex3")]),
        (71, [10, 34, 1]),  # DescriptorSet
        (71, [10, 33, 3]),  # Binding
        (22, [1, 32]),      # float
        (25, [20, 1, 3, 0, 0, 0, 1, 0]),  # image, Dim Cube, sampled
        (27, [21, 20]),     # sampled image
        (32, [22, 0, 21]), # UniformConstant pointer
        (59, [22, 10, 0]), # variable
    ])


def _ubo_module():
    return _module([
        (5, [40, *_string_words("ShiftVertexConstants")]),
        (71, [40, 34, 0]),
        (71, [40, 33, 14]),
        (30, [30]),        # empty struct
        (32, [31, 2, 30]), # Uniform pointer
        (59, [31, 40, 2]), # variable in Uniform storage
    ])


def test_reflects_sampler_cube_set_and_binding():
    report = reflect_spirv(_cube_module(), stage="pixel")
    assert report["ready"] is True
    assert report["descriptor_count"] == 1
    descriptor = report["descriptors"][0]
    assert descriptor["set"] == 1
    assert descriptor["binding"] == 3
    assert descriptor["descriptor_type"] == "combined-image-sampler"
    assert descriptor["resource_type"] == "samplerCube"
    assert descriptor["name"] == "tex3"
    assert descriptor["stage"] == "fragment"


def test_reflects_uniform_buffer_binding_14():
    report = reflect_spirv(_ubo_module(), stage="vertex")
    assert report["ready"] is True
    descriptor = report["descriptors"][0]
    assert descriptor["set"] == 0
    assert descriptor["binding"] == 14
    assert descriptor["descriptor_type"] == "uniform-buffer"
    assert descriptor["resource_type"] == "uniform-block"
    assert descriptor["stage"] == "vertex"


def test_reflection_rejects_descriptor_type_collision():
    instructions = [
        (71, [10, 34, 1]),
        (71, [10, 33, 3]),
        (71, [40, 34, 1]),
        (71, [40, 33, 3]),
        (22, [1, 32]),
        (25, [20, 1, 1, 0, 0, 0, 1, 0]),
        (27, [21, 20]),
        (32, [22, 0, 21]),
        (59, [22, 10, 0]),
        (30, [30]),
        (32, [31, 2, 30]),
        (59, [31, 40, 2]),
    ]
    report = reflect_spirv(_module(instructions), stage="pixel")
    assert report["ready"] is False
    assert any(
        reason == "spirv-reflection:descriptor-type-collision:set1:binding3"
        for reason in report["blocking_reasons"]
    )


def test_reflection_rejects_invalid_spirv_header():
    try:
        reflect_spirv(b"\0" * 20, stage="vertex")
    except ValueError as error:
        assert "magic" in str(error)
    else:
        raise AssertionError("invalid SPIR-V magic must be rejected")
