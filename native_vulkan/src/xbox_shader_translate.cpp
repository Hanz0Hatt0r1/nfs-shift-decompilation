#include "shift_xbox_shader_translate.hpp"

#include <algorithm>
#include <array>
#include <sstream>
#include <utility>

namespace shift::xbox {
namespace {

bool fail(const char* message, std::string* error) {
    if (error) *error = message;
    return false;
}

char component_name(uint32_t component) {
    static constexpr char kComponents[] = "xyzw";
    return kComponents[component & 3u];
}

bool fetch_selector(uint32_t selector, char* component) {
    if (selector < 4) {
        *component = component_name(selector);
        return true;
    }
    return false;
}

bool fetch_lane_expression(uint32_t selector, const char* source,
                           std::string* expression) {
    char component = 0;
    if (selector < 4) {
        fetch_selector(selector, &component);
        *expression = std::string(source) + "." + component;
    } else if (selector == 4) {
        *expression = "0.0";
    } else if (selector == 5) {
        *expression = "1.0";
    } else if (selector == 7) {
        expression->clear();
    } else {
        return false;
    }
    return true;
}

std::string constant_block(CapturedShaderStage stage) {
    if (stage == CapturedShaderStage::Vertex) {
        return "shift_vertex_constants";
    }
    return "shift_pixel_constants";
}

bool constant_relative(const CapturedShaderAluInstruction& instruction,
                       uint32_t source) {
    return source == 0 ? instruction.const0_relative
                       : source == 1 ? instruction.const1_relative : false;
}

std::string swizzled_vector(const CapturedShaderAluInstruction& instruction,
                            uint32_t source,
                            CapturedShaderStage stage) {
    std::string base;
    if (instruction.source_is_temporary[source]) {
        const uint32_t reg = instruction.source_temporary_registers[source];
        base = "r[" + std::to_string(reg) + "]";
        if (instruction.source_temporary_absolute[source]) {
            base = "abs(" + base + ")";
        }
    } else {
        const bool relative = constant_relative(instruction, source);
        const uint32_t reg = instruction.source_registers[source];
        base = constant_block(stage) + ".c[" + std::to_string(reg);
        if (relative) base += " + a0";
        base += "]";
    }

    std::string swizzle;
    for (uint32_t lane = 0; lane < 4; ++lane) {
        swizzle += component_name(
            captured_alu_source_component(instruction.source_swizzles[source], lane));
    }
    std::string result = base + "." + swizzle;
    if (instruction.source_negate[source]) result = "(-" + result + ")";
    return result;
}

std::string scalar_source(const CapturedShaderAluInstruction& instruction,
                          CapturedShaderStage stage) {
    const uint32_t source = 2;
    const uint32_t component =
        (3u + ((instruction.source_swizzles[source] >> 6) & 3u)) & 3u;
    std::string base;
    if (instruction.source_is_temporary[source]) {
        base = "r[" + std::to_string(
            instruction.source_temporary_registers[source]) + "]";
        if (instruction.source_temporary_absolute[source]) base = "abs(" + base + ")";
    } else {
        base = constant_block(stage) + ".c[" +
               std::to_string(instruction.source_registers[source]) + "]";
    }
    std::string result = base + "." + component_name(component);
    if (instruction.source_negate[source]) result = "(-" + result + ")";
    return result;
}

std::string scalar_constant(CapturedShaderStage stage, uint32_t reg,
                            uint32_t component) {
    return constant_block(stage) + ".c[" + std::to_string(reg) + "]." +
           component_name(component);
}

const char* vertex_input_type(uint32_t format) {
    switch (format) {
        case 57: return "vec3";
        case 38: return "vec4";
        default: return nullptr;
    }
}

bool append_fetch(std::ostringstream& glsl,
                  CapturedShaderStage stage,
                  const CapturedShaderFetchInstruction& fetch,
                  uint32_t vertex_input_location,
                  const CapturedShaderTranslationOptions& options,
                  bool* texture_declared,
                  uint32_t* sampler_register,
                  std::string* error) {
    if (fetch.source_relative || fetch.destination_relative || fetch.predicated) {
        return fail("captured shader fetch uses an unsupported relative or predicated form", error);
    }
    if (stage == CapturedShaderStage::Vertex) {
        const char* input_type = vertex_input_type(fetch.vertex_format);
        const uint32_t attribute_words = fetch.vertex_format == 57 ? 3u : 4u;
        if ((fetch.kind != CapturedShaderFetchKind::VertexFull &&
             fetch.kind != CapturedShaderFetchKind::VertexMini) ||
            !input_type || fetch.source_register != 0 ||
            fetch.destination_register >= 64 || fetch.vertex_stride == 0 ||
            fetch.vertex_offset < 0 ||
            static_cast<uint64_t>(fetch.vertex_offset) + attribute_words >
                fetch.vertex_stride || fetch.source_swizzle != 0) {
            return fail("captured vertex fetch is outside the float3/float4 layout", error);
        }
        const std::string input =
            "shift_vertex_input_" + std::to_string(vertex_input_location);
        const std::string fetched =
            "fetched_vertex_" + std::to_string(vertex_input_location);
        glsl << "  vec4 " << fetched << " = ";
        if (fetch.vertex_format == 57) {
            glsl << "vec4(" << input << ", 1.0);\n";
        } else {
            glsl << input << ";\n";
        }
        for (uint32_t lane = 0; lane < 4; ++lane) {
            const uint32_t selector = (fetch.destination_swizzle >> (lane * 3)) & 7u;
            std::string value;
            if (!fetch_lane_expression(selector, fetched.c_str(), &value)) {
                return fail("captured vertex fetch destination swizzle is unsupported", error);
            }
            if (!value.empty()) {
                glsl << "  r[" << fetch.destination_register << "]."
                     << component_name(lane) << " = " << value << ";\n";
            }
        }
        return true;
    }

    if (fetch.kind != CapturedShaderFetchKind::Texture2D ||
        fetch.fetch_constant_index > 15 || fetch.source_register != 0 ||
        fetch.destination_register != 0 || fetch.texture_dimension != 1 ||
        fetch.source_swizzle != 4) {
        return fail("captured texture fetch is outside the bound sampler-0 form", error);
    }
    for (uint32_t selector : options.texture_swizzle) {
        if (selector > 5) {
            return fail("captured texture descriptor swizzle is unsupported", error);
        }
    }
    const uint32_t sampler = fetch.fetch_constant_index;
    const uint32_t coord_x = fetch.source_swizzle & 3u;
    const uint32_t coord_y = (fetch.source_swizzle >> 2) & 3u;
    if (coord_x > 3 || coord_y > 3) {
        return fail("captured texture coordinate swizzle is unsupported", error);
    }
    glsl << "  vec4 sampled_" << sampler << " = texture(shift_sampler_"
         << sampler << ", r[0]." << component_name(coord_x)
         << component_name(coord_y) << ");\n  vec4 fetched_" << sampler << " = vec4(";
    for (uint32_t lane = 0; lane < 4; ++lane) {
        if (lane) glsl << ", ";
        const uint32_t selector = options.texture_swizzle[lane];
        if (selector < 4) glsl << "sampled_" << sampler << "." << component_name(selector);
        else glsl << (selector == 4 ? "0.0" : "1.0");
    }
    glsl << ");\n";
    for (uint32_t lane = 0; lane < 4; ++lane) {
        const uint32_t selector = (fetch.destination_swizzle >> (lane * 3)) & 7u;
        std::string value;
        if (!fetch_lane_expression(selector, ("fetched_" + std::to_string(sampler)).c_str(), &value)) {
            return fail("captured texture fetch destination swizzle is unsupported", error);
        }
        if (!value.empty()) glsl << "  r[" << fetch.destination_register << "]." << component_name(lane) << " = "
                                 << value << ";\n";
    }
    *texture_declared = true;
    *sampler_register = sampler;
    return true;
}

bool emit_alu(std::ostringstream& glsl,
              CapturedShaderStage stage,
              uint32_t address,
              const CapturedShaderAluInstruction& instruction,
              uint32_t allocation_type,
              std::string* error) {
    const auto fail_at_slot = [address, error](const char* reason) {
        if (error) {
            *error = std::string(reason) + " at instruction " +
                     std::to_string(address);
        }
        return false;
    };
    if (instruction.vector_destination_relative) {
        return fail_at_slot("captured ALU uses a relative vector destination");
    }
    // Xenos scalar-destination-relative addressing is relative to aL. The
    // current control-flow decoder rejects loop opcodes, so every shader that
    // reaches this emitter has the initial aL value (zero). Loop-aware shader
    // translation must replace this static mapping before accepting loops.
    if (instruction.absolute_constants) {
        return fail_at_slot("captured ALU uses absolute constants");
    }
    if (instruction.predicated) {
        return fail_at_slot("captured ALU is predicated");
    }
    for (uint32_t source = 0; source < 3; ++source) {
        if (instruction.source_temporary_relative[source]) {
            return fail_at_slot("captured ALU uses relative temporary addressing");
        }
        if (!instruction.source_is_temporary[source] &&
            constant_relative(instruction, source) &&
            !instruction.const_address_register_relative) {
            return fail_at_slot("captured ALU constant-relative source has no a0 selector");
        }
    }

    const std::string a = swizzled_vector(instruction, 0, stage);
    const std::string b = swizzled_vector(instruction, 1, stage);
    const std::string c = swizzled_vector(instruction, 2, stage);
    const std::string result = "alu_" + std::to_string(address);
    const uint32_t vector_result_mask = instruction.export_data ?
        instruction.vector_write_mask & ~instruction.scalar_write_mask :
        instruction.vector_write_mask;
    const uint32_t scalar_result_mask = instruction.export_data ?
        instruction.scalar_write_mask & ~instruction.vector_write_mask :
        instruction.scalar_write_mask;
    const uint32_t constant_one_mask = instruction.export_data ?
        instruction.vector_write_mask & instruction.scalar_write_mask : 0;
    const uint32_t constant_zero_mask =
        instruction.export_data && instruction.scalar_destination_relative ?
        0xFu & ~(instruction.vector_write_mask | instruction.scalar_write_mask) : 0;

    std::string export_target;
    if (instruction.export_data) {
        if (stage == CapturedShaderStage::Pixel) {
            if (allocation_type != 2) return fail("pixel export precedes color allocation", error);
            export_target = "shift_color0";
        } else if (allocation_type == 1) {
            export_target = "gl_Position";
        } else if (allocation_type == 2) {
            export_target = "shift_interpolator0";
        } else {
            return fail("vertex export has no supported output allocation", error);
        }
    }

    if (vector_result_mask != 0) {
        std::string operation;
        switch (instruction.vector_opcode) {
            case 1: operation = "(" + a + " * " + b + ")"; break;
            case 2: operation = "max(" + a + ", " + b + ")"; break;
            case 6:
                operation = "mix(vec4(0.0), vec4(1.0), greaterThanEqual(" + a + ", " + b + "))";
                break;
            case 11: operation = "fma(" + a + ", " + b + ", " + c + ")"; break;
            case 12: operation = "mix(" + c + ", " + b + ", equal(" + a + ", vec4(0.0)))"; break;
            case 15: operation = "vec4(dot(" + a + ", " + b + "))"; break;
            case 17: operation = "vec4(dot(" + a + ".xy, " + b + ".xy) + " + c + ".x)"; break;
            default: return fail("captured vertex/pixel ALU vector opcode is unsupported", error);
        }
        glsl << "  vec4 " << result << " = " << operation << ";\n";
        if (instruction.vector_clamp) {
            glsl << "  " << result << " = clamp(" << result
                 << ", vec4(0.0), vec4(1.0));\n";
        }
        std::string target;
        if (instruction.export_data) {
            target = export_target;
        } else {
            if (instruction.vector_destination >= 64) {
                return fail("captured vector destination is outside temporary register file", error);
            }
            target = "r[" + std::to_string(instruction.vector_destination) + "]";
        }
        for (uint32_t lane = 0; lane < 4; ++lane) {
            if (vector_result_mask & (1u << lane)) {
                glsl << "  " << target << "." << component_name(lane) << " = "
                     << result << "." << component_name(lane) << ";\n";
            }
        }
    }

    if (scalar_result_mask != 0) {
        std::string scalar;
        switch (instruction.scalar_opcode) {
            case 12:
                scalar = "trunc(" + scalar_source(instruction, stage) + ")";
                break;
            case 42:
                if (instruction.source_is_temporary[2]) {
                    return fail("captured MULSC0 constant operand is not a constant", error);
                }
                scalar = scalar_constant(stage, instruction.source_registers[2],
                                         instruction.scalar_constant_component) +
                         " * r[" + std::to_string(instruction.scalar_temporary_register) +
                         "]." + component_name(instruction.scalar_temporary_component);
                break;
            default:
                return fail("captured ALU scalar opcode writes an unsupported result", error);
        }
        if (instruction.scalar_clamp) scalar = "clamp(" + scalar + ", 0.0, 1.0)";
        std::string target;
        if (instruction.export_data) {
            target = export_target;
        } else {
            if (instruction.scalar_destination >= 64) {
                return fail("captured scalar destination is outside temporary register file", error);
            }
            target = "r[" + std::to_string(instruction.scalar_destination) + "]";
        }
        for (uint32_t lane = 0; lane < 4; ++lane) {
            if (scalar_result_mask & (1u << lane)) {
                glsl << "  " << target << "." << component_name(lane)
                     << " = " << scalar << ";\n";
            }
        }
    } else if (instruction.scalar_opcode == 23) {
        const std::string address_value = scalar_source(instruction, stage);
        glsl << "  a0 = clamp(int(floor(" << address_value
             << " + 0.5)), -256, 255);\n";
    } else if (!(instruction.export_data && instruction.scalar_write_mask != 0) &&
               instruction.scalar_opcode != 50 && instruction.scalar_opcode != 5) {
        return fail("captured ALU scalar opcode is unsupported", error);
    }
    for (uint32_t lane = 0; lane < 4; ++lane) {
        if (constant_one_mask & (1u << lane)) {
            glsl << "  " << export_target << "." << component_name(lane) << " = 1.0;\n";
        } else if (constant_zero_mask & (1u << lane)) {
            glsl << "  " << export_target << "." << component_name(lane) << " = 0.0;\n";
        }
    }
    return true;
}

}  // namespace

bool translate_captured_shader_glsl(
    CapturedShaderStage stage,
    const uint8_t* shader_bytes,
    size_t byte_length,
    const CapturedShaderTranslationOptions& options,
    CapturedShaderTranslation* output,
    std::string* error) {
    if (!shader_bytes || !output) return fail("invalid captured shader translation input", error);

    std::vector<CapturedShaderControlFlow> control_flow;
    std::vector<CapturedShaderInstructionSchedule> schedule;
    if (!decode_captured_shader_control_flow(shader_bytes, byte_length,
                                             &control_flow, error) ||
        !schedule_captured_shader_instructions(control_flow, byte_length,
                                               &schedule, error)) {
        return false;
    }

    std::vector<uint32_t> path;
    uint32_t pc = 0;
    for (size_t steps = 0; steps <= control_flow.size(); ++steps) {
        if (pc >= control_flow.size()) return fail("captured shader control flow leaves its prefix", error);
        const CapturedShaderControlFlow& clause = control_flow[pc];
        path.push_back(pc);
        if (clause.opcode == ShaderControlFlowOpcode::ExecEnd) break;
        if (clause.opcode == ShaderControlFlowOpcode::ConditionalJump) {
            if (clause.predicated || clause.jump_direction) {
                return fail("captured shader branch uses unsupported predicate/direction", error);
            }
            bool take = clause.unconditional;
            if (!clause.unconditional) {
                bool value = false;
                if (clause.bool_constant == 128) value = options.pixel_b128;
                else if (clause.bool_constant == 129) value = options.pixel_b129;
                else return fail("captured shader branch uses an uncaptured bool constant", error);
                take = value == clause.condition;
            }
            if (take) {
                if (clause.address <= pc) return fail("captured shader loop is unsupported", error);
                pc = clause.address;
            } else {
                ++pc;
            }
            continue;
        }
        if (clause.opcode != ShaderControlFlowOpcode::Nop &&
            clause.opcode != ShaderControlFlowOpcode::Exec &&
            clause.opcode != ShaderControlFlowOpcode::Allocate) {
            return fail("captured shader control-flow opcode is unsupported", error);
        }
        ++pc;
    }
    if (path.empty() || control_flow[path.back()].opcode != ShaderControlFlowOpcode::ExecEnd) {
        return fail("captured shader path has no bounded exec-end", error);
    }

    std::vector<CapturedShaderInstructionSchedule> executed;
    std::vector<CapturedShaderFetchInstruction> executed_fetches;
    std::vector<CapturedVertexInputAttribute> vertex_input_attributes;
    bool has_texture = false;
    uint32_t sampler_register = 0;
    bool has_vertex_fetch_constant = false;
    uint32_t vertex_fetch_constant_index = 0;
    CapturedShaderFetchInstruction preceding_vertex_full{};
    bool has_preceding_vertex_full = false;
    for (uint32_t slot : path) {
        const auto& clause = control_flow[slot];
        if (clause.opcode != ShaderControlFlowOpcode::Exec &&
            clause.opcode != ShaderControlFlowOpcode::ExecEnd) continue;
        for (const auto& instruction : schedule) {
            if (instruction.control_flow_index == slot) {
                executed.push_back(instruction);
                if (instruction.kind == ShaderScheduledInstructionKind::Fetch) {
                    CapturedShaderFetchInstruction fetch{};
                    if (!decode_captured_shader_fetch_instruction(
                            shader_bytes + instruction.address * 12, 12, &fetch, error)) return false;
                    if (stage == CapturedShaderStage::Vertex) {
                        CapturedShaderFetchInstruction effective_fetch{};
                        if (!inherit_captured_vertex_fetch_fields(
                                fetch,
                                has_preceding_vertex_full
                                    ? &preceding_vertex_full
                                    : nullptr,
                                &effective_fetch, error)) {
                            return false;
                        }
                        if (effective_fetch.kind == CapturedShaderFetchKind::VertexFull) {
                            preceding_vertex_full = effective_fetch;
                            has_preceding_vertex_full = true;
                        }
                        if (has_vertex_fetch_constant &&
                            vertex_fetch_constant_index !=
                                effective_fetch.fetch_constant_index) {
                            return fail("captured vertex shader uses multiple fetch constants", error);
                        }
                        has_vertex_fetch_constant = true;
                        vertex_fetch_constant_index =
                            effective_fetch.fetch_constant_index;
                        const uint32_t location =
                            static_cast<uint32_t>(vertex_input_attributes.size());
                        vertex_input_attributes.push_back({
                            location,
                            effective_fetch.destination_register,
                            effective_fetch.vertex_format,
                            effective_fetch.vertex_stride,
                            effective_fetch.vertex_offset,
                        });
                        executed_fetches.push_back(effective_fetch);
                    } else {
                        if (fetch.kind == CapturedShaderFetchKind::Texture2D) {
                            if (has_texture &&
                                sampler_register != fetch.fetch_constant_index) {
                                return fail("captured pixel shader uses multiple samplers", error);
                            }
                            has_texture = true;
                            sampler_register = fetch.fetch_constant_index;
                        }
                        executed_fetches.push_back(fetch);
                    }
                }
            }
        }
    }

    std::ostringstream glsl;
    glsl << "#version 450\n";
    if (stage == CapturedShaderStage::Vertex) {
        for (const CapturedVertexInputAttribute& attribute : vertex_input_attributes) {
            const char* type = vertex_input_type(attribute.vertex_format);
            if (!type) {
                return fail("captured vertex format is outside the float3/float4 layout", error);
            }
            glsl << "layout(location=" << attribute.location << ") in " << type
                 << " shift_vertex_input_" << attribute.location << ";\n";
        }
        glsl << "layout(location=0) out vec4 shift_interpolator0;\n"
             << "layout(set=0,binding=14,std140) uniform ShiftVertexConstants { vec4 c[256]; } shift_vertex_constants;\n";
    } else {
        glsl << "layout(location=0) in vec4 shift_interpolator0;\n"
             << "layout(location=0) out vec4 shift_color0;\n"
             << "layout(set=0,binding=15,std140) uniform ShiftPixelConstants { vec4 c[256]; } shift_pixel_constants;\n";
        if (has_texture) {
            glsl << "layout(set=1,binding=0) uniform sampler2D shift_sampler_"
                 << sampler_register << ";\n";
        }
    }
    glsl << "void main() {\n  vec4 r[64];\n"
         << "  for (int i=0; i<64; ++i) r[i]=vec4(0.0);\n"
         << "  int a0=0;\n";
    if (stage == CapturedShaderStage::Vertex) {
        glsl << "  r[0].x=float(gl_VertexIndex);\n  gl_Position=vec4(0.0);\n"
             << "  gl_PointSize=1.0;\n"
             << "  shift_interpolator0=vec4(0.0);\n";
    } else {
        glsl << "  r[0]=shift_interpolator0;\n  shift_color0=vec4(0.0);\n";
    }

    uint32_t allocation_type = 0;
    size_t fetch_index = 0;
    std::vector<uint32_t> float_constant_registers;
    bool uses_relative_float_constant_index = false;
    const auto record_constant_source =
        [&float_constant_registers, &uses_relative_float_constant_index](
            const CapturedShaderAluInstruction& alu, uint32_t source,
            std::string* record_error) {
            if (alu.source_is_temporary[source]) return true;
            if (constant_relative(alu, source)) {
                uses_relative_float_constant_index = true;
                if (!alu.const_address_register_relative) {
                    if (record_error) {
                        *record_error =
                            "captured shader constant-relative source has no a0 selector";
                    }
                    return false;
                }
                return true;
            }
            const uint32_t index = alu.source_registers[source];
            if (index >= 256) {
                if (record_error) {
                    *record_error = "captured shader float constant index is out of range";
                }
                return false;
            }
            float_constant_registers.push_back(index);
            return true;
        };
    for (uint32_t slot : path) {
        const auto& clause = control_flow[slot];
        if (clause.opcode == ShaderControlFlowOpcode::Allocate) {
            const uint32_t expected = stage == CapturedShaderStage::Vertex ?
                (clause.allocation_type == 1 ? 1u : 2u) : 2u;
            if (clause.allocation_type != expected) {
                return fail("captured shader output allocation is unsupported", error);
            }
            allocation_type = expected;
            continue;
        }
        if (clause.opcode != ShaderControlFlowOpcode::Exec &&
            clause.opcode != ShaderControlFlowOpcode::ExecEnd) continue;
        for (const auto& instruction : executed) {
            if (instruction.control_flow_index != slot) continue;
            if (instruction.kind == ShaderScheduledInstructionKind::Fetch) {
                if (fetch_index >= executed_fetches.size()) {
                    return fail("captured shader fetch schedule changed during translation", error);
                }
                const CapturedShaderFetchInstruction& fetch =
                    executed_fetches[fetch_index];
                if (!append_fetch(glsl, stage, fetch,
                                  static_cast<uint32_t>(fetch_index), options,
                                  &has_texture, &sampler_register, error)) {
                    return false;
                }
                ++fetch_index;
            } else {
                CapturedShaderAluInstruction alu{};
                if (!decode_captured_shader_alu_instruction(
                        shader_bytes + instruction.address * 12, 12, &alu, error)) {
                    return false;
                }
                const uint32_t vector_result_mask = alu.export_data ?
                    alu.vector_write_mask & ~alu.scalar_write_mask :
                    alu.vector_write_mask;
                const uint32_t scalar_result_mask = alu.export_data ?
                    alu.scalar_write_mask & ~alu.vector_write_mask :
                    alu.scalar_write_mask;
                if (vector_result_mask != 0) {
                    const uint32_t sources[] = {0, 1, 2};
                    const size_t source_count =
                        alu.vector_opcode == 11 || alu.vector_opcode == 12 ? 3 : 2;
                    for (size_t i = 0; i < source_count; ++i) {
                        if (!record_constant_source(alu, sources[i], error)) return false;
                    }
                }
                if (scalar_result_mask != 0 || alu.scalar_opcode == 23) {
                    if (!record_constant_source(alu, 2, error)) return false;
                }
                if (!emit_alu(glsl, stage, instruction.address, alu,
                              allocation_type, error)) return false;
            }
        }
    }
    glsl << "}\n";

    CapturedShaderTranslation translated{};
    translated.glsl = glsl.str();
    translated.vertex_input_attributes = std::move(vertex_input_attributes);
    translated.has_vertex_fetch_constant = has_vertex_fetch_constant;
    translated.vertex_fetch_constant_index = vertex_fetch_constant_index;
    translated.uses_texture = has_texture;
    translated.texture_fetch_constant_index = sampler_register;
    std::sort(float_constant_registers.begin(), float_constant_registers.end());
    float_constant_registers.erase(
        std::unique(float_constant_registers.begin(),
                    float_constant_registers.end()),
        float_constant_registers.end());
    translated.float_constant_registers = std::move(float_constant_registers);
    translated.uses_relative_float_constant_index =
        uses_relative_float_constant_index;
    translated.executed_instruction_addresses.reserve(executed.size());
    for (const auto& instruction : executed) {
        translated.executed_instruction_addresses.push_back(instruction.address);
    }
    *output = std::move(translated);
    if (error) error->clear();
    return true;
}

}  // namespace shift::xbox
