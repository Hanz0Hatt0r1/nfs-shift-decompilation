#include "shift_xbox_shader_translate.hpp"

#include <algorithm>
#include <array>
#include <map>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <limits>
#include <sstream>
#include <utility>

namespace shift::xbox {
namespace {

constexpr uint32_t kVertexInterpolatorCount = 16;

bool fail(const char* message, std::string* error) {
    if (error) *error = message;
    return false;
}

std::string glsl_float(float value) {
    std::ostringstream result;
    result << std::setprecision(std::numeric_limits<float>::max_digits10) << value;
    std::string literal = result.str();
    if (literal.find_first_of(".eE") == std::string::npos) literal += ".0";
    return literal;
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
    switch (source) {
        case 0:
            return instruction.const0_relative;
        case 1:
            return instruction.source_is_temporary[0]
                ? instruction.const0_relative
                : instruction.const1_relative;
        case 2:
            return instruction.source_is_temporary[0] &&
                           instruction.source_is_temporary[1]
                ? instruction.const0_relative
                : instruction.const1_relative;
        default:
            return false;
    }
}

bool scalar_constant_temporary_opcode(uint32_t opcode) {
    return opcode >= 42 && opcode <= 47;
}

// Loop-relative (aL) constant addressing. The translator statically unrolls
// Xenos loops, so every reachable instruction instance knows its aL value:
// aL = iterator * step + start, from xenos::LoopConstant (xenos.h).
// In the reference translator (translator.cpp) a constant operand that is
// addressed but NOT address-register-relative is kLoopRelative - i.e. aL - not
// an error, which is what the previous code assumed.
std::string al_operand(bool address_register_relative, int32_t al_value) {
    return address_register_relative ? std::string("a0")
                                     : std::to_string(al_value);
}

std::string swizzled_vector(const CapturedShaderAluInstruction& instruction,
                            uint32_t source,
                            CapturedShaderStage stage,
                            int32_t al_value) {
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
        // Loop-relative (aL) addressing is resolved at translation time: the
        // translator unrolls loops, so every reachable instruction instance has
        // a statically known aL value. See xenos::LoopConstant in xenos.h
        // (aL = iterator * step + start) and translator.cpp, where a constant
        // operand with const_address_register_relative clear is kLoopRelative
        // rather than an error.
        if (relative) {
            base += " + " +
                    al_operand(instruction.const_address_register_relative, al_value);
        }
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

std::string scalar_source_component(
    const CapturedShaderAluInstruction& instruction,
    CapturedShaderStage stage, uint32_t source_component, int32_t al_value) {
    const uint32_t source = 2;
    const uint32_t component = captured_alu_source_component(
        instruction.source_swizzles[source], source_component);
    std::string base;
    if (instruction.source_is_temporary[source]) {
        base = "r[" + std::to_string(
            instruction.source_temporary_registers[source]) + "]";
        if (instruction.source_temporary_absolute[source]) base = "abs(" + base + ")";
    } else {
        base = constant_block(stage) + ".c[" +
               std::to_string(instruction.source_registers[source]);
        if (constant_relative(instruction, source)) {
            base += " + " + al_operand(
                instruction.const_address_register_relative, al_value);
        }
        base += "]";
    }
    std::string result = base + "." + component_name(component);
    if (instruction.source_negate[source]) result = "(-" + result + ")";
    return result;
}

std::string scalar_source(const CapturedShaderAluInstruction& instruction,
                          CapturedShaderStage stage, int32_t al_value) {
    return scalar_source_component(instruction, stage, 3, al_value);
}

std::string scalar_source_x(const CapturedShaderAluInstruction& instruction,
                            CapturedShaderStage stage, int32_t al_value) {
    return scalar_source_component(instruction, stage, 0, al_value);
}

std::string scalar_multiply(const std::string& a, const std::string& b) {
    // D3D9 flushes zero and denormal scalar multiply operands to +0.
    constexpr char kMinNormal[] = "1.1754943508222875e-38";
    return "((" + a + " == 0.0 || abs(" + a + ") < " + kMinNormal +
           " || " + b + " == 0.0 || abs(" + b + ") < " + kMinNormal +
           ") ? 0.0 : (" + a + " * " + b + "))";
}

std::string scalar_constant(CapturedShaderStage stage, uint32_t reg,
                            uint32_t component, bool relative,
                            bool address_register_relative, int32_t al_value) {
    return constant_block(stage) + ".c[" + std::to_string(reg) +
           (relative ? " + " +
                           al_operand(address_register_relative, al_value)
                     : "") +
           "]." + component_name(component);
}

const char* vertex_input_type(uint32_t format) {
    switch (format) {
        case 6: return "vec4";
        case 37: return "vec2";
        case 57: return "vec3";
        case 38: return "vec4";
        default: return nullptr;
    }
}

uint32_t vertex_input_words(uint32_t format) {
    switch (format) {
        case 6: return 1;
        case 37: return 2;
        case 57: return 3;
        case 38: return 4;
        default: return 0;
    }
}

const char* vertex_format_name(uint32_t format) {
    switch (format) {
        case 6: return "8_8_8_8";
        case 7: return "2_10_10_10";
        case 16: return "10_11_11";
        case 17: return "11_11_10";
        case 25: return "16_16";
        case 26: return "16_16_16_16";
        case 31: return "16_16_FLOAT";
        case 32: return "16_16_16_16_FLOAT";
        case 33: return "32";
        case 34: return "32_32";
        case 35: return "32_32_32_32";
        case 36: return "32_FLOAT";
        case 37: return "32_32_FLOAT";
        case 38: return "32_32_32_32_FLOAT";
        case 57: return "32_32_32_FLOAT";
        default: return "unknown";
    }
}

bool append_fetch(std::ostringstream& glsl,
                  CapturedShaderStage stage,
                  const CapturedShaderFetchInstruction& fetch,
                  uint32_t fetch_ordinal,
                  bool disambiguate_texture_symbols,
                  const CapturedShaderTranslationOptions& options,
                  bool* texture_declared,
                  uint32_t* sampler_register,
                  std::string* error) {
    if (fetch.source_relative || fetch.destination_relative || fetch.predicated) {
        return fail("captured shader fetch uses an unsupported relative or predicated form", error);
    }
    if (stage == CapturedShaderStage::Vertex) {
        const char* input_type = vertex_input_type(fetch.vertex_format);
        const uint32_t attribute_words = vertex_input_words(fetch.vertex_format);
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
            "shift_vertex_input_" + std::to_string(fetch_ordinal);
        const std::string fetched =
            "fetched_vertex_" + std::to_string(fetch_ordinal);
        glsl << "  vec4 " << fetched << " = ";
        if (fetch.vertex_format == 57) {
            glsl << "vec4(" << input << ", 1.0);\n";
        } else if (fetch.vertex_format == 37) {
            glsl << "vec4(" << input << ", 0.0, 1.0);\n";
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
        fetch.fetch_constant_index >= 32 || fetch.source_register >= 64 ||
        fetch.destination_register >= 64 || fetch.texture_dimension != 1) {
        std::ostringstream message;
        message << "captured texture fetch is outside the supported direct 2D form: "
                   "fetch_constant=" << fetch.fetch_constant_index
                << " source_register=" << fetch.source_register
                << " destination_register=" << fetch.destination_register
                << " source_swizzle=" << fetch.source_swizzle
                << " destination_swizzle=0x" << std::hex
                << fetch.destination_swizzle << std::dec
                << " dimension=" << fetch.texture_dimension
                << " source_relative=" << fetch.source_relative
                << " destination_relative=" << fetch.destination_relative
                << " predicated=" << fetch.predicated
                << " predicate_condition=" << fetch.predicate_condition;
        if (error) *error = message.str();
        return false;
    }
    const CapturedShaderTextureOptions& texture_options =
        options.textures[fetch.fetch_constant_index];
    for (uint32_t selector : texture_options.swizzle) {
        if (selector > 5) {
            return fail("captured texture descriptor swizzle is unsupported", error);
        }
    }
    for (TextureSign sign : texture_options.signs) {
        // TextureSign::Signed is GPUSIGN two's complement texel data. The
        // renderer binds such fetches through an SNORM image view, so the
        // sampled value already carries the correct signed normalization and
        // no per-channel fixup is emitted (unlike Gamma below).
        if (sign != TextureSign::Unsigned && sign != TextureSign::Gamma &&
            sign != TextureSign::Signed) {
            std::ostringstream message;
            message << "captured texture channel sign is outside the unsigned/gamma/signed subset"
                    << " fetch_constant=" << fetch.fetch_constant_index
                    << " signs=[";
            for (size_t lane = 0; lane < texture_options.signs.size(); ++lane) {
                if (lane) message << ',';
                message << static_cast<uint32_t>(texture_options.signs[lane]);
            }
            message << ']';
            if (error) *error = message.str();
            return false;
        }
    }
    const uint32_t sampler = fetch.fetch_constant_index;
    const uint32_t coord_x = fetch.source_swizzle & 3u;
    const uint32_t coord_y = (fetch.source_swizzle >> 2) & 3u;
    const std::string symbol_suffix = disambiguate_texture_symbols
        ? "_fetch_" + std::to_string(fetch_ordinal)
        : std::string{};
    const std::string sampled = "sampled_" + std::to_string(sampler) +
                                symbol_suffix;
    const std::string fetched = "fetched_" + std::to_string(sampler) +
                                symbol_suffix;
    glsl << "  vec4 " << sampled << " = texture(shift_sampler_"
         << sampler << ", r[" << fetch.source_register << "]."
         << component_name(coord_x)
         << component_name(coord_y) << ");\n";
    if (texture_options.integer_scale != 0) {
        glsl << "  " << sampled << " *= "
             << texture_options.integer_scale << ".0;\n";
    }
    for (uint32_t lane = 0; lane < 4; ++lane) {
        if (texture_options.signs[lane] == TextureSign::Gamma) {
            glsl << "  " << sampled << '.' << component_name(lane)
                 << "=shift_pwl_gamma_to_linear(" << sampled << '.'
                 << component_name(lane) << ");\n";
        }
    }
    glsl << "  vec4 " << fetched << " = vec4(";
    for (uint32_t lane = 0; lane < 4; ++lane) {
        if (lane) glsl << ", ";
        const uint32_t selector = texture_options.swizzle[lane];
        if (selector < 4) glsl << sampled << "." << component_name(selector);
        else glsl << (selector == 4 ? "0.0" : "1.0");
    }
    glsl << ");\n";
    for (uint32_t lane = 0; lane < 4; ++lane) {
        const uint32_t selector = (fetch.destination_swizzle >> (lane * 3)) & 7u;
        std::string value;
        if (!fetch_lane_expression(selector, fetched.c_str(), &value)) {
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
              int32_t al_value,
              uint32_t emission_index,
              std::string* error) {
    const auto fail_at_slot = [address, error](const std::string& reason) {
        if (error) {
            *error = reason + " at instruction " +
                     std::to_string(address);
        }
        return false;
    };
    const uint32_t vector_result_mask = instruction.export_data ?
        instruction.vector_write_mask & ~instruction.scalar_write_mask :
        instruction.vector_write_mask;
    const uint32_t scalar_result_mask = instruction.export_data ?
        instruction.scalar_write_mask & ~instruction.vector_write_mask :
        instruction.scalar_write_mask;
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
    const bool scalar_constant_temporary =
        scalar_constant_temporary_opcode(instruction.scalar_opcode);
    const bool vector_uses_third_source = vector_result_mask != 0 &&
        (instruction.vector_opcode == 11 || instruction.vector_opcode == 12);
    for (uint32_t source = 0; source < 3; ++source) {
        // For mulsc/addsc/subsc, src3_sel contributes to the scalar temporary
        // register index. The scalar constant remains src3_reg even when this
        // selector is set, so don't interpret its packed bits as temp flags.
        if (source == 2 && scalar_constant_temporary &&
            !vector_uses_third_source) {
            continue;
        }
        if (instruction.source_temporary_relative[source]) {
            return fail_at_slot("captured ALU uses relative temporary addressing");
        }
        // A constant operand can be relative through either aL (loop, statically
        // resolved by unrolling) or a0 (address register). Both are supported;
        // the aL/a0 choice is made at emission time by al_operand().
    }
    // See above: relative scalar-constant operands are supported through both
    // aL (statically resolved) and a0.

    const std::string a = swizzled_vector(instruction, 0, stage, al_value);
    const std::string b = swizzled_vector(instruction, 1, stage, al_value);
    const std::string c = swizzled_vector(instruction, 2, stage, al_value);
    // A loop body re-emitted by unrolling repeats its instruction address. The
    // first emission keeps the historical `alu_<address>` symbol; repeats get a
    // disambiguating suffix so the generated GLSL stays valid.
    const std::string result = emission_index == 0
        ? "alu_" + std::to_string(address)
        : "alu_" + std::to_string(address) + "_" + std::to_string(emission_index);
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
            if (instruction.vector_destination >= kVertexInterpolatorCount) {
                return fail_at_slot("captured vertex interpolator export index exceeds 15");
            }
            export_target = "shift_interpolator" +
                           std::to_string(instruction.vector_destination);
        } else {
            return fail("vertex export has no supported output allocation", error);
        }
    }

    if (vector_result_mask != 0) {
        std::string operation;
        switch (instruction.vector_opcode) {
            case 0: operation = "(" + a + " + " + b + ")"; break;
            case 1: operation = "(" + a + " * " + b + ")"; break;
            case 2: operation = "max(" + a + ", " + b + ")"; break;
            case 3:
                // Xenos MIN selects src0 only when src0 < src1, including
                // the source operand choice when either value is unordered.
                operation = "mix(" + b + ", " + a + ", lessThan(" + a +
                            ", " + b + "))";
                break;
            case 5:
                // Xenos SGT: per-component src0 > src1 ? 1.0 : 0.0.
                operation = "mix(vec4(0.0), vec4(1.0), greaterThan(" + a + ", " + b + "))";
                break;
            case 6:
                operation = "mix(vec4(0.0), vec4(1.0), greaterThanEqual(" + a + ", " + b + "))";
                break;
            case 11: operation = "fma(" + a + ", " + b + ", " + c + ")"; break;
            case 12: operation = "mix(" + c + ", " + b + ", equal(" + a + ", vec4(0.0)))"; break;
            case 15: operation = "vec4(dot(" + a + ", " + b + "))"; break;
            case 16: operation = "vec4(dot(" + a + ".xyz, " + b + ".xyz))"; break;
            case 17: operation = "vec4(dot(" + a + ".xy, " + b + ".xy) + " + c + ".x)"; break;
            default: {
                std::ostringstream message;
                message << "captured vertex/pixel ALU vector opcode "
                        << instruction.vector_opcode << " is unsupported";
                return fail_at_slot(message.str());
            }
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

    std::string scalar;
    switch (instruction.scalar_opcode) {
            case 5:
                scalar = "(" + scalar_source(instruction, stage, al_value) + " >= " +
                         scalar_source_x(instruction, stage, al_value) + " ? " +
                         scalar_source(instruction, stage, al_value) + " : " +
                         scalar_source_x(instruction, stage, al_value) + ")";
                break;
            case 6:
                scalar = "(" + scalar_source(instruction, stage, al_value) + " < " +
                         scalar_source_x(instruction, stage, al_value) + " ? " +
                         scalar_source(instruction, stage, al_value) + " : " +
                         scalar_source_x(instruction, stage, al_value) + ")";
                break;
            case 23:
                scalar = "(" + scalar_source(instruction, stage, al_value) + " >= " +
                         scalar_source_x(instruction, stage, al_value) + " ? " +
                         scalar_source(instruction, stage, al_value) + " : " +
                         scalar_source_x(instruction, stage, al_value) + ")";
                break;
            case 12:
                scalar = "trunc(" + scalar_source(instruction, stage, al_value) + ")";
                break;
            case 13:
                scalar = "floor(" + scalar_source(instruction, stage, al_value) + ")";
                break;
            case 27:
            case 28:
            case 29:
            case 30: {
                // Floating-point predicate set (ucode.h kSetpEq/Ne/Gt/Ge).
                // Each writes dest.xyzw = 0.0 when the test passes and 1.0
                // otherwise, and additionally assigns the predicate register.
                // The predicate side effect is not modelled here: it is tracked
                // separately, and a predicated branch that would observe it is
                // rejected instead of silently mis-resolved.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                const char* test = instruction.scalar_opcode == 27 ? " == 0.0"
                                 : instruction.scalar_opcode == 28 ? " != 0.0"
                                 : instruction.scalar_opcode == 29 ? " > 0.0"
                                                                   : " >= 0.0";
                scalar = "((" + operand + test + ") ? 0.0 : 1.0)";
                break;
            }
            case 33:
                // setp_clr: dest.xyzw = FLT_MAX, p0 = 0.
                scalar = "3.402823466e+38";
                break;
            case 0:
            case 1: {
                // adds / adds_prev: dest = src0.a + (src0.a for adds,
                // previous scalar for adds_prev). ucode.h kAdds/kAddsPrev.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                const std::string addend = instruction.scalar_opcode == 0
                    ? operand
                    : "previous_scalar";
                scalar = "(" + operand + " + " + addend + ")";
                break;
            }
            case 2:
            case 3: {
                // muls / muls_prev: dest = src0.a * (src0.b for muls,
                // previous scalar for muls_prev). ucode.h kMuls/kMulsPrev.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                const std::string factor = instruction.scalar_opcode == 2
                    ? scalar_source_x(instruction, stage, al_value)
                    : std::string("previous_scalar");
                scalar = scalar_multiply(operand, factor);
                break;
            }
            case 4: {
                // muls_prev2/MUL_PREV2s: -FLT_MAX when the previous scalar or
                // src0.b is not usable, otherwise src0.a * ps (ucode.h).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                const std::string b = scalar_source_x(instruction, stage, al_value);
                scalar = "((previous_scalar == -3.402823466e+38 || "
                         "!isfinite(previous_scalar) || !isfinite(" + b + ") || " +
                         b + " <= 0.0) ? -3.402823466e+38 : " + operand +
                         " * previous_scalar)";
                break;
            }
            case 7:
                // seqs/SETEs: dest = src0.a == 0.0 ? 1.0 : 0.0.
                scalar = "((" + scalar_source(instruction, stage, al_value) +
                         " == 0.0) ? 1.0 : 0.0)";
                break;
            case 8:
                // sgts/SETGTs: dest = src0.a > 0.0 ? 1.0 : 0.0.
                scalar = "((" + scalar_source(instruction, stage, al_value) +
                         " > 0.0) ? 1.0 : 0.0)";
                break;
            case 9:
                // sges/SETGTEs: dest = src0.a >= 0.0 ? 1.0 : 0.0.
                scalar = "((" + scalar_source(instruction, stage, al_value) +
                         " >= 0.0) ? 1.0 : 0.0)";
                break;
            case 10:
                // snes/SETNEs: dest = src0.a != 0.0 ? 1.0 : 0.0.
                scalar = "((" + scalar_source(instruction, stage, al_value) +
                         " != 0.0) ? 1.0 : 0.0)";
                break;
            case 11:
                // frcs/FRACs: dest = src0.a - floor(src0.a).
                scalar = "fract(" + scalar_source(instruction, stage, al_value) + ")";
                break;
            case 15: {
                // logc/LOG_CLAMP: log2 clamped to -FLT_MAX instead of -INF.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 1.0 ? 0.0 : max(log2(" + operand +
                         "), -3.402823466e+38))";
                break;
            }
            case 17:
            case 18: {
                // rcpc/RECIP_CLAMP and rcpf/RECIP_FF: clamped reciprocal.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 1.0 ? 1.0 : clamp(1.0 / " + operand +
                         ", -3.402823466e+38, 3.402823466e+38))";
                break;
            }
            case 20:
            case 21: {
                // rsqc/RECIPSQ_CLAMP and rsqf/RECIPSQ_FF: clamped reciprocal
                // square root.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 1.0 ? 1.0 : clamp(1.0 / sqrt(abs(" +
                         operand + ")), -3.402823466e+38, 3.402823466e+38))";
                break;
            }
            case 22: {
                // rsq/RSQ_IEEE: dest = src0.a == 1.0 ? 1.0 : 1/sqrt(|src0.a|).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 1.0 ? 1.0 : 1.0 / sqrt(abs(" +
                         operand + ")))";
                break;
            }
            case 24:
                // maxas/MAXAs: dest = max(src0.a, |src0.b|).
                scalar = "max(" + scalar_source(instruction, stage, al_value) +
                         ", abs(" + scalar_source_x(instruction, stage, al_value) + "))";
                break;
            case 25:
            case 26: {
                // subs / subs_prev: dest = src0.a - (src0.b for subs,
                // previous scalar for subs_prev).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                const std::string subtrahend = instruction.scalar_opcode == 25
                    ? scalar_source_x(instruction, stage, al_value)
                    : std::string("previous_scalar");
                scalar = "(" + operand + " - " + subtrahend + ")";
                break;
            }
            case 31: {
                // setp_inv: dest = 1.0 at zero, else src0.a (ucode.h kSetpInv).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 1.0 ? 0.0 : (" + operand +
                         " == 0.0 ? 1.0 : " + operand + "))";
                break;
            }
            case 32: {
                // setp_pop: dest = src0.a - 1.0 clamped at 0 (ucode.h kSetpPop).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "((" + operand + " - 1.0 <= 0.0) ? 0.0 : (" + operand +
                         " - 1.0))";
                break;
            }
            case 34: {
                // setp_rstr: dest = 0.0 when src0.a is zero, else src0.a.
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 0.0 ? 0.0 : " + operand + ")";
                break;
            }
            case 14: {
                // exp/EXP_IEEE: dest = src0.a == 0.0 ? 1.0 : pow(2, src0.a)
                // (ucode.h AluScalarOpcode::kExp).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 0.0 ? 1.0 : exp2(" + operand + "))";
                break;
            }
            case 19: {
                // Xenos rcp/RECIP_IEEE: dest = src0.a == 1.0 ? 1.0 : 1.0 / src0.a
                // (ucode.h AluScalarOpcode::kRcp).
                const std::string operand =
                    scalar_source(instruction, stage, al_value);
                scalar = "(" + operand + " == 1.0 ? 1.0 : 1.0 / " + operand + ")";
                break;
            }
            case 16:
                // Xenos LOG_IEEE computes log2(src0.a). The captured scalar
                // source selector is already decoded by scalar_source().
                scalar = "log2(" + scalar_source(instruction, stage, al_value) + ")";
                break;
            case 42:
            case 43:
            case 44:
            case 45:
            case 46:
            case 47: {
                // Xenos mulsc/addsc/subsc use c#.w as the left operand and
                // the scalar temporary selected by opcode[0], src3_sel, and
                // src3_swiz as the right operand. src3_reg_negate applies to
                // both operands. See xenia-project/xenia src/xenia/gpu/ucode.h
                // (AluInstruction::scalar_const_reg_op_src_temp_reg).
                std::string constant_operand = scalar_constant(
                    stage, instruction.source_registers[2],
                    instruction.scalar_constant_component,
                    constant_relative(instruction, 2),
                    instruction.const_address_register_relative, al_value);
                std::string temporary_operand =
                    "r[" + std::to_string(instruction.scalar_temporary_register) +
                    "]." + component_name(instruction.scalar_temporary_component);
                if (instruction.source_negate[2]) {
                    constant_operand = "(-" + constant_operand + ")";
                    temporary_operand = "(-" + temporary_operand + ")";
                }
                switch (instruction.scalar_opcode) {
                    case 42:
                    case 43:
                        scalar = scalar_multiply(constant_operand, temporary_operand);
                        break;
                    case 44:
                    case 45:
                        scalar = "(" + constant_operand + " + " +
                                 temporary_operand + ")";
                        break;
                    case 46:
                    case 47:
                        scalar = "(" + constant_operand + " - " +
                                 temporary_operand + ")";
                        break;
                }
                break;
            }
            case 50:
                scalar = "previous_scalar";
                break;
            default: {
                std::ostringstream message;
                message << "captured ALU scalar opcode " << instruction.scalar_opcode
                        << " writes an unsupported result";
                return fail_at_slot(message.str());
            }
    }
    if (instruction.scalar_opcode != 50) {
        // Every scalar opcode except RETAIN_PREV replaces ps, even when its
        // scalar destination mask is empty.
        glsl << "  previous_scalar = " << scalar << ";\n";
    }
    if (scalar_result_mask != 0) {
        const std::string scalar_output = instruction.scalar_clamp ?
            "clamp(previous_scalar, 0.0, 1.0)" : "previous_scalar";
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
                     << " = " << scalar_output << ";\n";
            }
        }
    }
    if (instruction.scalar_opcode == 23) {
        const std::string address_value = scalar_source(instruction, stage, al_value);
        glsl << "  a0 = clamp(int(floor(" << address_value
             << " + 0.5)), -256, 255);\n";
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
    if (stage == CapturedShaderStage::Vertex &&
        options.clip_disabled_window_coordinates &&
        (!options.window_coordinate_width || !options.window_coordinate_height ||
         !std::isfinite(options.window_coordinate_x_scale) ||
         !std::isfinite(options.window_coordinate_y_scale) ||
         !std::isfinite(options.window_coordinate_x_offset) ||
         !std::isfinite(options.window_coordinate_y_offset))) {
        return fail("captured clip-disabled window transform is invalid", error);
    }

    std::vector<CapturedShaderControlFlow> control_flow;
    std::vector<CapturedShaderInstructionSchedule> schedule;
    if (!decode_captured_shader_control_flow(shader_bytes, byte_length,
                                             &control_flow, error) ||
        !schedule_captured_shader_instructions(control_flow, byte_length,
                                               &schedule, error)) {
        return false;
    }

    // Can this clause assign the predicate register? The predicate writers are
    // kSetp* (scalar 27-34) and kSetp*Push (vector 20-23), per ucode.h. The
    // predicate at a branch depends only on instructions already executed, so
    // tracking writes along the path is both sufficient and precise - a write
    // that happens later in the shader cannot affect an earlier branch.
    const auto clause_writes_predicate = [&](uint32_t clause_slot) {
        for (const CapturedShaderInstructionSchedule& scheduled : schedule) {
            if (scheduled.control_flow_index != clause_slot) continue;
            if (scheduled.kind != ShaderScheduledInstructionKind::Alu) continue;
            CapturedShaderAluInstruction alu{};
            if (!decode_captured_shader_alu_instruction(
                    shader_bytes + scheduled.address * 12, 12, &alu, nullptr)) {
                continue;
            }
            if ((alu.vector_opcode >= 20 && alu.vector_opcode <= 23) ||
                (alu.scalar_opcode >= 27 && alu.scalar_opcode <= 34)) {
                return true;
            }
        }
        return false;
    };
    // True once an already-executed instruction on the path assigned the
    // predicate, making the runtime value unknown at translation time.
    bool predicate_written_on_path = false;

    struct PathEntry { uint32_t slot; int32_t al_value; };
    std::vector<PathEntry> path;
    // Loop bodies are unrolled statically using the captured loop constants.
    // The Xenos loop is `LoopStart` (skip target + loop_id) ... `LoopEnd`
    // (body start + loop_id + predicated-break condition); see
    // rex::graphics::ucode::ControlFlowLoopStartInstruction / ...LoopEnd and
    // the reference sequencer in interpreter.cpp. Each stack entry remembers
    // the LoopStart clause index, the recorded iteration and the trip count so
    // the body can be emitted exactly trip_count times with no dynamic loop in
    // the generated GLSL.
    struct ActiveLoop {
        uint32_t start_clause;
        uint32_t iteration;
        uint32_t trip_count;
        int32_t al_start;
        int32_t al_step;
    };
    std::vector<ActiveLoop> active_loops;
    // aL for the innermost active loop iteration: iterator * step + start.
    const auto current_al = [&active_loops]() -> int32_t {
        if (active_loops.empty()) return 0;
        const ActiveLoop& loop = active_loops.back();
        return static_cast<int32_t>(loop.iteration) * loop.al_step + loop.al_start;
    };
    uint32_t unrolled_clause_budget = options.loop_unroll_limit == 0
        ? 32u
        : options.loop_unroll_limit * 8u;
    uint32_t pc = 0;
    for (size_t steps = 0; steps <= control_flow.size() + unrolled_clause_budget;
         ++steps) {
        if (pc >= control_flow.size()) return fail("captured shader control flow leaves its prefix", error);
        const CapturedShaderControlFlow& clause = control_flow[pc];
        if (clause.opcode == ShaderControlFlowOpcode::ExecEnd) {
            path.push_back(PathEntry{pc, 0});
            break;
        }
        if (clause.opcode == ShaderControlFlowOpcode::LoopStart) {
            if (clause.loop_id >= options.loop_constants.size() ||
                !options.loop_constant_valid[clause.loop_id]) {
                std::ostringstream message;
                message << "captured shader loop uses an uncaptured loop constant "
                        << "(loop_id=" << clause.loop_id << ')';
                if (error) *error = message.str();
                return false;
            }
            if (active_loops.size() >= 4) {
                return fail("captured shader loop nesting exceeds the supported depth",
                            error);
            }
            const uint32_t constant = options.loop_constants[clause.loop_id];
            const uint32_t trip_count = constant & 0xFFu;
            if (trip_count > (options.loop_unroll_limit == 0 ? 32u
                                                            : options.loop_unroll_limit)) {
                std::ostringstream message;
                message << "captured shader loop trip count exceeds the unroll limit "
                        << "(loop_id=" << clause.loop_id
                        << " count=" << trip_count << ')';
                if (error) *error = message.str();
                return false;
            }
            const int32_t al_start = static_cast<int32_t>((constant >> 8) & 0xFFu);
            const int32_t al_step = static_cast<int32_t>(
                static_cast<int8_t>((constant >> 16) & 0xFFu));
            path.push_back(PathEntry{pc, 0});
            if (trip_count == 0) {
                // Zero iterations: jump straight to the skip target after the
                // matching LoopEnd.
                if (clause.address <= pc) {
                    return fail("captured shader loop skip target is not forward", error);
                }
                pc = clause.address;
                continue;
            }
            active_loops.push_back(
                ActiveLoop{pc, 0u, trip_count, al_start, al_step});
            ++pc;
            continue;
        }
        if (clause.opcode == ShaderControlFlowOpcode::LoopEnd) {
            if (active_loops.empty()) {
                return fail("captured shader loop end has no matching loop start", error);
            }
            ActiveLoop& loop = active_loops.back();
            if (loop.iteration + 1u < loop.trip_count) {
                path.push_back(PathEntry{pc, current_al()});
                // Advance the iterator, then re-enter the body right after the
                // LoopStart clause. The increment must happen before the next
                // clause is recorded, because current_al() is sampled when a
                // clause is pushed.
                ++loop.iteration;
                pc = loop.start_clause + 1u;
                continue;
            }
            path.push_back(PathEntry{pc, 0});
            active_loops.pop_back();
            ++pc;
            continue;
        }
        if (clause.opcode == ShaderControlFlowOpcode::ConditionalJump) {
            path.push_back(PathEntry{pc, 0});
            // jump_direction only says whether the target is before or after
            // this instruction; both are legal, so it is not a rejection
            // reason (the reference sequencer just inverts the target).
            bool take = clause.unconditional;
            if (!clause.unconditional) {
                bool value = false;
                if (clause.predicated) {
                    // A predicated branch tests the predicate register instead
                    // of a bool constant (interpreter.cpp kCondJmp). Retail
                    // menu shaders that take this path never assign the
                    // predicate, so it holds its reset value of false; a shader
                    // that does assign it cannot be resolved statically.
                    if (predicate_written_on_path) {
                        std::ostringstream message;
                        message << "captured shader predicated branch follows a "
                                   "dynamic predicate write (instruction="
                                << pc << ", address=" << clause.address << ')';
                        if (error) *error = message.str();
                        return false;
                    }
                    value = false;
                } else if (clause.bool_constant == 128) {
                    value = options.pixel_b128;
                } else if (clause.bool_constant == 129) {
                    value = options.pixel_b129;
                } else {
                    return fail(
                        "captured shader branch uses an uncaptured bool constant",
                        error);
                }
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
        if (clause.opcode == ShaderControlFlowOpcode::ConditionalExec ||
            clause.opcode == ShaderControlFlowOpcode::ConditionalExecEnd) {
            bool value = false;
            if (clause.bool_constant == 128) value = options.pixel_b128;
            else if (clause.bool_constant == 129) value = options.pixel_b129;
            else {
                return fail("captured shader conditional exec uses an uncaptured bool constant",
                            error);
            }
            const bool execute = value == clause.condition;
            if (execute) {
                path.push_back(PathEntry{pc, 0});
                if (clause.opcode == ShaderControlFlowOpcode::ConditionalExecEnd) {
                    break;
                }
            }
            ++pc;
            continue;
        }
        if (clause.opcode != ShaderControlFlowOpcode::Nop &&
            clause.opcode != ShaderControlFlowOpcode::Exec &&
            clause.opcode != ShaderControlFlowOpcode::ConditionalExec &&
            clause.opcode != ShaderControlFlowOpcode::ConditionalExecEnd &&
            clause.opcode != ShaderControlFlowOpcode::Allocate) {
            return fail("captured shader control-flow opcode is unsupported", error);
        }
        path.push_back(PathEntry{pc, current_al()});
        ++pc;
    }
    if (path.empty() ||
        (control_flow[path.back().slot].opcode != ShaderControlFlowOpcode::ExecEnd &&
         control_flow[path.back().slot].opcode !=
             ShaderControlFlowOpcode::ConditionalExecEnd)) {
        return fail("captured shader path has no bounded exec-end", error);
    }

    std::vector<CapturedShaderInstructionSchedule> executed;
    std::vector<CapturedShaderFetchInstruction> executed_fetches;
    std::vector<CapturedVertexInputAttribute> vertex_input_attributes;
    std::vector<uint32_t> texture_fetch_constant_indices;
    bool has_texture = false;
    uint32_t sampler_register = 0;
    bool has_vertex_fetch_constant = false;
    uint32_t vertex_fetch_constant_index = 0;
    CapturedShaderFetchInstruction preceding_vertex_full{};
    bool has_preceding_vertex_full = false;
    // Instructions executed by each path entry, in emission order. Unrolled
    // loops repeat the same clause index, so per-path-entry lists (rather than
    // a flat list keyed by clause) are required to keep the two passes aligned.
    std::vector<std::vector<CapturedShaderInstructionSchedule>> path_instructions;
    path_instructions.reserve(path.size());
    for (const PathEntry& entry : path) {
        path_instructions.emplace_back();
        const auto& clause = control_flow[entry.slot];
        if (clause.opcode != ShaderControlFlowOpcode::Exec &&
            clause.opcode != ShaderControlFlowOpcode::ExecEnd &&
            clause.opcode != ShaderControlFlowOpcode::ConditionalExec &&
            clause.opcode != ShaderControlFlowOpcode::ConditionalExecEnd) continue;
        for (const auto& instruction : schedule) {
            if (instruction.control_flow_index == entry.slot) {
                path_instructions.back().push_back(instruction);
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
                            if (std::find(texture_fetch_constant_indices.begin(),
                                          texture_fetch_constant_indices.end(),
                                          fetch.fetch_constant_index) ==
                                texture_fetch_constant_indices.end()) {
                                texture_fetch_constant_indices.push_back(
                                    fetch.fetch_constant_index);
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

    std::array<uint32_t, 32> texture_fetch_counts{};
    for (const CapturedShaderFetchInstruction& fetch : executed_fetches) {
        if (fetch.kind == CapturedShaderFetchKind::Texture2D) {
            ++texture_fetch_counts[fetch.fetch_constant_index];
        }
    }

    std::ostringstream glsl;
    glsl << "#version 450\n";
    if (stage == CapturedShaderStage::Vertex) {
        for (const CapturedVertexInputAttribute& attribute : vertex_input_attributes) {
            const char* type = vertex_input_type(attribute.vertex_format);
            if (!type) {
                std::ostringstream message;
                message << "captured vertex format is outside the float3/float4 layout: "
                           "shader_bytes=" << byte_length << " attributes="
                        << vertex_input_attributes.size() << " rejected={location="
                        << attribute.location << ",destination=r"
                        << attribute.destination_register << ",format="
                        << attribute.vertex_format << '('
                        << vertex_format_name(attribute.vertex_format) << ")"
                        << ",stride_dwords=" << attribute.stride_dwords
                        << ",offset_dwords=" << attribute.offset_dwords << '}';
                for (const CapturedVertexInputAttribute& other :
                     vertex_input_attributes) {
                    if (&other == &attribute) continue;
                    message << " other{location=" << other.location
                            << ",destination=r" << other.destination_register
                            << ",format=" << other.vertex_format << '('
                            << vertex_format_name(other.vertex_format) << ")"
                            << ",stride_dwords=" << other.stride_dwords
                            << ",offset_dwords=" << other.offset_dwords << '}';
                }
                if (error) *error = message.str();
                return false;
            }
            glsl << "layout(location=" << attribute.location << ") in " << type
                 << " shift_vertex_input_" << attribute.location << ";\n";
        }
        for (uint32_t index = 0; index < kVertexInterpolatorCount; ++index) {
            glsl << "layout(location=" << index << ") out vec4 shift_interpolator"
                 << index << ";\n";
        }
        glsl << "layout(set=0,binding=14,std140) uniform ShiftVertexConstants { vec4 c[256]; } shift_vertex_constants;\n";
    } else {
        for (uint32_t index = 0; index < kVertexInterpolatorCount; ++index) {
            glsl << "layout(location=" << index << ") in vec4 shift_interpolator"
                 << index << ";\n";
        }
        glsl << "layout(location=0) out vec4 shift_color0;\n"
             << "layout(set=0,binding=15,std140) uniform ShiftPixelConstants { vec4 c[256]; } shift_pixel_constants;\n";
        for (uint32_t texture_index : texture_fetch_constant_indices) {
            glsl << "layout(set=1,binding=" << texture_index
                 << ") uniform sampler2D shift_sampler_"
                 << texture_index << ";\n";
        }
    }
    const bool uses_gamma_texture = std::any_of(
        texture_fetch_constant_indices.begin(), texture_fetch_constant_indices.end(),
        [&options](uint32_t index) {
            const auto& signs = options.textures[index].signs;
            return std::find(signs.begin(), signs.end(), TextureSign::Gamma) !=
                   signs.end();
        });
    if (stage == CapturedShaderStage::Pixel && uses_gamma_texture) {
        glsl << "float shift_pwl_gamma_to_linear(float gamma) {\n"
             << "  gamma=clamp(gamma,0.0,1.0);\n"
             << "  float scale=gamma>=192.0/255.0 ? 8.0/1024.0 : "
                "gamma>=96.0/255.0 ? 4.0/1024.0 : "
                "gamma>=64.0/255.0 ? 2.0/1024.0 : 1.0/1024.0;\n"
             << "  float offset=gamma>=192.0/255.0 ? -1024.0 : "
                "gamma>=96.0/255.0 ? -256.0 : "
                "gamma>=64.0/255.0 ? -64.0 : 0.0;\n"
             << "  float linear=gamma*(255.0*1024.0)*scale+offset;\n"
             << "  return (linear+trunc(linear*scale))/1023.0;\n"
             << "}\n";
    }
    glsl << "void main() {\n  vec4 r[64];\n"
         << "  for (int i=0; i<64; ++i) r[i]=vec4(0.0);\n"
         << "  int a0=0;\n  float previous_scalar=0.0;\n";
    if (stage == CapturedShaderStage::Vertex) {
        glsl << "  r[0].x=float(gl_VertexIndex);\n  gl_Position=vec4(0.0);\n"
             << "  gl_PointSize=1.0;\n";
        for (uint32_t index = 0; index < kVertexInterpolatorCount; ++index) {
            glsl << "  shift_interpolator" << index << "=vec4(0.0);\n";
        }
    } else {
        for (uint32_t index = 0; index < kVertexInterpolatorCount; ++index) {
            glsl << "  r[" << index << "]=shift_interpolator" << index << ";\n";
        }
        glsl << "  shift_color0=vec4(0.0);\n";
    }

    uint32_t allocation_type = 0;
    size_t fetch_index = 0;
    std::vector<uint32_t> float_constant_registers;
    bool uses_relative_float_constant_index = false;
    const auto record_constant_source =
        [&float_constant_registers, &uses_relative_float_constant_index](
            const CapturedShaderAluInstruction& alu, uint32_t source,
            bool scalar_constant_temporary,
            std::string* record_error) {
            if (!scalar_constant_temporary && alu.source_is_temporary[source]) {
                return true;
            }
            if (constant_relative(alu, source)) {
                // aL-relative operands are resolved to a literal offset while
                // unrolling, so only a0-relative accesses need the dynamic
                // address register to be tracked as a constant index range.
                if (alu.const_address_register_relative) {
                    uses_relative_float_constant_index = true;
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
    // How many times each instruction address has already been emitted. A
    // statically unrolled loop emits its body more than once.
    std::map<uint32_t, uint32_t> emitted_address_counts;
    for (size_t path_index = 0; path_index < path.size(); ++path_index) {
        const PathEntry& entry = path[path_index];
        const uint32_t slot = entry.slot;
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
            clause.opcode != ShaderControlFlowOpcode::ExecEnd &&
            clause.opcode != ShaderControlFlowOpcode::ConditionalExec &&
            clause.opcode != ShaderControlFlowOpcode::ConditionalExecEnd) continue;
        for (const auto& instruction : path_instructions[path_index]) {
            if (instruction.kind == ShaderScheduledInstructionKind::Fetch) {
                if (fetch_index >= executed_fetches.size()) {
                    return fail("captured shader fetch schedule changed during translation", error);
                }
                const CapturedShaderFetchInstruction& fetch =
                    executed_fetches[fetch_index];
                const bool disambiguate_texture_symbols =
                    stage == CapturedShaderStage::Pixel &&
                    fetch.kind == CapturedShaderFetchKind::Texture2D &&
                    texture_fetch_counts[fetch.fetch_constant_index] > 1;
                if (!append_fetch(glsl, stage, fetch,
                                  static_cast<uint32_t>(fetch_index),
                                  disambiguate_texture_symbols, options,
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
                        if (!record_constant_source(alu, sources[i], false, error)) {
                            return false;
                        }
                    }
                }
                if (scalar_constant_temporary_opcode(alu.scalar_opcode)) {
                    if (!record_constant_source(alu, 2, true, error)) {
                        return false;
                    }
                } else if (alu.scalar_opcode != 50) {
                    if (!record_constant_source(alu, 2, false, error)) return false;
                }
                const uint32_t emission_index =
                    emitted_address_counts[instruction.address]++;
                if (!emit_alu(glsl, stage, instruction.address, alu,
                              allocation_type, entry.al_value, emission_index,
                              error)) {
                    return false;
                }
            }
        }
    }
    if (stage == CapturedShaderStage::Pixel && options.gamma_color_target) {
        // Xenos RGBA8_GAMMA encodes RGB before storing to the render target;
        // alpha stays linear. The copied surface contains these encoded bytes.
        glsl << "  vec3 linear_rgb=clamp(shift_color0.rgb,0.0,1.0);\n"
             << "  vec3 gamma_scale=mix(vec3(1023.0),vec3(1023.0/2.0),"
                "step(vec3(64.0/1023.0),linear_rgb));\n"
             << "  gamma_scale=mix(gamma_scale,vec3(1023.0/4.0),"
                "step(vec3(128.0/1023.0),linear_rgb));\n"
             << "  gamma_scale=mix(gamma_scale,vec3(1023.0/8.0),"
                "step(vec3(512.0/1023.0),linear_rgb));\n"
             << "  vec3 gamma_offset=mix(vec3(0.0),vec3(32.0),"
                "step(vec3(64.0/1023.0),linear_rgb));\n"
             << "  gamma_offset=mix(gamma_offset,vec3(64.0),"
                "step(vec3(128.0/1023.0),linear_rgb));\n"
             << "  gamma_offset=mix(gamma_offset,vec3(128.0),"
                "step(vec3(512.0/1023.0),linear_rgb));\n"
             << "  shift_color0.rgb=(trunc(linear_rgb*gamma_scale)+gamma_offset)"
                "/255.0;\n";
    }
    if (stage == CapturedShaderStage::Vertex &&
        options.clip_disabled_window_coordinates) {
        const float width = static_cast<float>(options.window_coordinate_width);
        const float height = static_cast<float>(options.window_coordinate_height);
        glsl << "  gl_Position = vec4("
             << "((gl_Position.x * " << glsl_float(options.window_coordinate_x_scale)
             << " + " << glsl_float(options.window_coordinate_x_offset)
             << " - " << glsl_float(width * 0.5f) << ") * "
             << glsl_float(2.0f / width) << "), "
             << "((gl_Position.y * " << glsl_float(options.window_coordinate_y_scale)
             << " + " << glsl_float(options.window_coordinate_y_offset)
             << " - " << glsl_float(height * 0.5f) << ") * "
             << glsl_float(2.0f / height) << "), gl_Position.z, 1.0);\n";
    }
    glsl << "}\n";

    CapturedShaderTranslation translated{};
    translated.glsl = glsl.str();
    translated.vertex_input_attributes = std::move(vertex_input_attributes);
    translated.has_vertex_fetch_constant = has_vertex_fetch_constant;
    translated.vertex_fetch_constant_index = vertex_fetch_constant_index;
    translated.uses_texture = has_texture;
    translated.texture_fetch_constant_index = texture_fetch_constant_indices.empty()
        ? 0u : texture_fetch_constant_indices.front();
    translated.texture_fetch_constant_indices =
        std::move(texture_fetch_constant_indices);
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

namespace {

template <typename T>
void append_key_value(std::string& key, T value) {
    key.append(reinterpret_cast<const char*>(&value), sizeof(value));
}

void append_key_float(std::string& key, float value) {
    uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    append_key_value(key, bits);
}

}  // namespace

std::string CapturedShaderTranslationCache::make_key(
    CapturedShaderStage stage, const uint8_t* shader_bytes,
    size_t byte_length,
    const CapturedShaderTranslationOptions& options) {
    std::string key;
    key.reserve(byte_length + 1600);
    append_key_value(key, static_cast<uint8_t>(stage));
    append_key_value(key, static_cast<uint64_t>(byte_length));
    if (byte_length != 0) {
        key.append(reinterpret_cast<const char*>(shader_bytes), byte_length);
    }
    append_key_value(key, static_cast<uint8_t>(options.pixel_b128));
    append_key_value(key, static_cast<uint8_t>(options.pixel_b129));
    append_key_value(key, static_cast<uint8_t>(options.gamma_color_target));
    append_key_value(
        key, static_cast<uint8_t>(options.clip_disabled_window_coordinates));
    append_key_value(key, options.window_coordinate_width);
    append_key_value(key, options.window_coordinate_height);
    append_key_float(key, options.window_coordinate_x_scale);
    append_key_float(key, options.window_coordinate_y_scale);
    append_key_float(key, options.window_coordinate_x_offset);
    append_key_float(key, options.window_coordinate_y_offset);
    for (const CapturedShaderTextureOptions& texture : options.textures) {
        for (uint32_t selector : texture.swizzle) append_key_value(key, selector);
        for (TextureSign sign : texture.signs) {
            append_key_value(key, static_cast<uint8_t>(sign));
        }
    }
    return key;
}

size_t CapturedShaderTranslationCache::translation_payload_bytes(
    const CapturedShaderTranslation& translation) {
    return sizeof(translation) + translation.glsl.size() +
           translation.executed_instruction_addresses.size() * sizeof(uint32_t) +
           translation.vertex_input_attributes.size() *
               sizeof(CapturedVertexInputAttribute) +
           translation.texture_fetch_constant_indices.size() * sizeof(uint32_t) +
           translation.float_constant_registers.size() * sizeof(uint32_t);
}

bool CapturedShaderTranslationCache::translate(
    CapturedShaderStage stage, const uint8_t* shader_bytes, size_t byte_length,
    const CapturedShaderTranslationOptions& options,
    CapturedShaderTranslation* output, std::string* error) {
    // Avoid retaining or copying unusually large guest programs. They still go
    // through the original translator and its normal validation path.
    if (byte_length > kMaximumPayloadBytes || (byte_length && !shader_bytes)) {
        ++misses_;
        return translate_captured_shader_glsl(stage, shader_bytes, byte_length,
                                               options, output, error);
    }

    std::string key = make_key(stage, shader_bytes, byte_length, options);
    if (const auto found = entries_.find(key); found != entries_.end()) {
        ++hits_;
        *output = found->second.translation;
        if (error) error->clear();
        return true;
    }

    ++misses_;
    CapturedShaderTranslation translated{};
    if (!translate_captured_shader_glsl(stage, shader_bytes, byte_length,
                                         options, &translated, error)) {
        return false;
    }
    *output = translated;

    const size_t payload_bytes = key.size() * 2u +
                                 translation_payload_bytes(translated);
    if (payload_bytes > kMaximumPayloadBytes) return true;

    while (!insertion_order_.empty() &&
           (entries_.size() >= kMaximumEntries ||
            retained_payload_bytes_ + payload_bytes > kMaximumPayloadBytes)) {
        const std::string& oldest = insertion_order_.front();
        const auto victim = entries_.find(oldest);
        if (victim != entries_.end()) {
            retained_payload_bytes_ -= victim->second.payload_bytes;
            entries_.erase(victim);
        }
        insertion_order_.pop_front();
    }

    auto [stored, inserted] = entries_.emplace(
        std::move(key), Entry{std::move(translated), payload_bytes});
    if (inserted) {
        retained_payload_bytes_ += payload_bytes;
        insertion_order_.push_back(stored->first);
    }
    return true;
}

void CapturedShaderTranslationCache::clear() {
    entries_.clear();
    insertion_order_.clear();
    retained_payload_bytes_ = 0;
    hits_ = 0;
    misses_ = 0;
}

CapturedShaderTranslationCache::Stats CapturedShaderTranslationCache::stats() const {
    return Stats{hits_, misses_, entries_.size(), retained_payload_bytes_};
}

}  // namespace shift::xbox
