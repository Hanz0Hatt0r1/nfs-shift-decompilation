#include "shift_xbox_draw_input.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <utility>

namespace shift::xbox {
namespace {

constexpr uint32_t kType3Header = 0xC0000000u;
constexpr uint32_t kPacketTypeMask = 0xC0000000u;
constexpr uint32_t kPacketCountMask = 0x3FFF0000u;
constexpr uint32_t kPacketOpcodeMask = 0x0000FF00u;
constexpr uint32_t kDrawIndxOpcode = 0x22u;
constexpr uint32_t kTriangleList = 4u;
constexpr uint32_t kIndexCountMask = 0x00FFFFFFu;
constexpr uint32_t kDmaSwapModeMask = 0xC0000000u;
constexpr size_t kCapturedPacketBytes = 20;

uint64_t tiled_2d_offset_32bpp(uint32_t x, uint32_t y, uint32_t pitch_pixels) {
    const uint64_t outer_blocks =
        ((static_cast<uint64_t>(y >> 5) * (pitch_pixels >> 5)) + (x >> 5)) << 6;
    const uint64_t inner_blocks = (((y >> 1) & 0x7u) << 3) | (x & 0x7u);
    const uint64_t outer_inner_bytes = (outer_blocks | inner_blocks) << 2;
    const uint32_t bank = (y >> 4) & 1u;
    const uint32_t pipe = ((x >> 3) & 3u) ^ (((y >> 3) & 1u) << 1);

    return (static_cast<uint64_t>(y & 1u) << 4) |
           (static_cast<uint64_t>(pipe) << 6) |
           (static_cast<uint64_t>(bank) << 11) |
           (outer_inner_bytes & 0xFu) |
           (((outer_inner_bytes >> 4) & 1u) << 5) |
           (((outer_inner_bytes >> 5) & 7u) << 8) |
           (outer_inner_bytes >> 8 << 12);
}

uint32_t read_be32(const uint8_t* bytes) {
    return (static_cast<uint32_t>(bytes[0]) << 24) |
           (static_cast<uint32_t>(bytes[1]) << 16) |
           (static_cast<uint32_t>(bytes[2]) << 8) |
           static_cast<uint32_t>(bytes[3]);
}

bool fail(const char* message, std::string* error) {
    if (error) {
        *error = message;
    }
    return false;
}

float register_float(uint32_t bits) {
    static_assert(sizeof(float) == sizeof(bits), "32-bit register float required");
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

bool viewport_dimension(float half_extent, uint32_t* extent) {
    if (!std::isfinite(half_extent) || half_extent <= 0.0f) {
        return false;
    }
    const double pixels = std::round(static_cast<double>(half_extent) * 2.0);
    if (pixels < 1.0 || pixels > std::numeric_limits<uint32_t>::max()) {
        return false;
    }
    *extent = static_cast<uint32_t>(pixels);
    return static_cast<double>(half_extent) * 2.0 == pixels;
}

}  // namespace

bool scan_captured_packet_stream(
    const uint8_t* stream_bytes,
    size_t byte_length,
    std::vector<PacketSpan>* output,
    std::string* error) {
    if (!output || (byte_length && !stream_bytes)) {
        return fail("invalid PM4 packet stream input", error);
    }
    if ((byte_length & 3u) != 0) {
        return fail("PM4 packet stream is not dword-aligned", error);
    }

    std::vector<PacketSpan> packets;
    size_t offset = 0;
    while (offset < byte_length) {
        const uint32_t header = read_be32(stream_bytes + offset);
        const uint32_t type = header >> 30;
        uint64_t packet_words = 1;
        if (header == 0) {
            // A zero dword is the command processor's single-dword NOP.
        } else if (type == 0 || type == 3) {
            // Type-0 and type-3 count fields encode payload_dwords - 1.
            packet_words = static_cast<uint64_t>((header >> 16) & 0x3FFFu) + 2;
        } else if (type == 1) {
            packet_words = 3;
        }

        const uint64_t packet_bytes = packet_words * sizeof(uint32_t);
        if (packet_bytes > byte_length - offset) {
            return fail("truncated PM4 packet in stream", error);
        }

        packets.push_back(PacketSpan{
            header == 0 ? PacketType::ZeroNop : static_cast<PacketType>(type),
            offset,
            static_cast<size_t>(packet_bytes),
            type == 3 ? (header & kPacketOpcodeMask) >> 8 : 0u,
        });
        offset += static_cast<size_t>(packet_bytes);
    }

    *output = std::move(packets);
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_shader_control_flow(
    const uint8_t* shader_bytes,
    size_t byte_length,
    std::vector<CapturedShaderControlFlow>* output,
    std::string* error) {
    constexpr uint32_t kControlFlowNop = 0;
    constexpr uint32_t kControlFlowExec = 1;
    constexpr uint32_t kControlFlowExecEnd = 2;
    constexpr uint32_t kControlFlowConditionalJump = 11;
    constexpr uint32_t kControlFlowAllocate = 12;
    constexpr uint32_t kControlFlowTripletBytes = 12;

    if (!shader_bytes || !output || byte_length == 0 ||
        (byte_length % kControlFlowTripletBytes) != 0 ||
        byte_length / kControlFlowTripletBytes >
            std::numeric_limits<uint32_t>::max()) {
        return fail("invalid captured shader bytecode size", error);
    }

    const uint32_t triplet_count =
        static_cast<uint32_t>(byte_length / kControlFlowTripletBytes);
    uint32_t control_flow_triplet_count = triplet_count;
    for (uint32_t triplet = 0; triplet < control_flow_triplet_count; ++triplet) {
        const uint8_t* bytes = shader_bytes + triplet * kControlFlowTripletBytes;
        const uint32_t dword0 = read_be32(bytes);
        const uint32_t dword1 = read_be32(bytes + 4);
        const uint32_t dword2 = read_be32(bytes + 8);
        const uint32_t words[4] = {
            dword0,
            dword1 & 0xFFFFu,
            (dword1 >> 16) | (dword2 << 16),
            dword2 >> 16,
        };

        for (uint32_t slot = 0; slot < 2; ++slot) {
            const uint32_t opcode = (words[slot * 2 + 1] >> 12) & 0xFu;
            if (opcode == kControlFlowExec || opcode == kControlFlowExecEnd) {
                control_flow_triplet_count = std::min(
                    control_flow_triplet_count, words[slot * 2] & 0xFFFu);
            }
        }
    }
    if (control_flow_triplet_count == 0 ||
        control_flow_triplet_count >= triplet_count) {
        return fail("captured shader has no bounded control-flow prefix", error);
    }

    std::vector<CapturedShaderControlFlow> instructions;
    instructions.reserve(control_flow_triplet_count * 2);
    for (uint32_t triplet = 0; triplet < control_flow_triplet_count; ++triplet) {
        const uint8_t* bytes = shader_bytes + triplet * kControlFlowTripletBytes;
        const uint32_t dword0 = read_be32(bytes);
        const uint32_t dword1 = read_be32(bytes + 4);
        const uint32_t dword2 = read_be32(bytes + 8);
        const uint32_t words[4] = {
            dword0,
            dword1 & 0xFFFFu,
            (dword1 >> 16) | (dword2 << 16),
            dword2 >> 16,
        };

        for (uint32_t slot = 0; slot < 2; ++slot) {
            const uint32_t word0 = words[slot * 2];
            const uint32_t word1 = words[slot * 2 + 1];
            const uint32_t raw_opcode = (word1 >> 12) & 0xFu;
            if (raw_opcode != kControlFlowNop && raw_opcode != kControlFlowExec &&
                raw_opcode != kControlFlowExecEnd &&
                raw_opcode != kControlFlowConditionalJump &&
                raw_opcode != kControlFlowAllocate) {
                return fail("unsupported captured shader control-flow opcode", error);
            }

            CapturedShaderControlFlow decoded{};
            decoded.instruction_index = triplet * 2 + slot;
            decoded.opcode = static_cast<ShaderControlFlowOpcode>(raw_opcode);
            if (raw_opcode == kControlFlowExec || raw_opcode == kControlFlowExecEnd) {
                decoded.address = word0 & 0xFFFu;
                decoded.instruction_count = (word0 >> 12) & 0x7u;
                decoded.sequence = (word0 >> 16) & 0xFFFu;
                if (decoded.instruction_count == 0 ||
                    static_cast<uint64_t>(decoded.address) + decoded.instruction_count >
                        triplet_count) {
                    return fail("captured shader exec range is invalid", error);
                }
            } else if (raw_opcode == kControlFlowConditionalJump) {
                decoded.address = word0 & 0x1FFFu;
                decoded.unconditional = ((word0 >> 13) & 1u) != 0;
                decoded.predicated = ((word0 >> 14) & 1u) != 0;
                decoded.jump_direction = ((word1 >> 1) & 1u) != 0;
                decoded.bool_constant = (word1 >> 2) & 0xFFu;
                decoded.condition = ((word1 >> 10) & 1u) != 0;
                if (static_cast<uint64_t>(decoded.address) >=
                    static_cast<uint64_t>(control_flow_triplet_count) * 2) {
                    return fail("captured shader jump target is out of range", error);
                }
            } else if (raw_opcode == kControlFlowAllocate) {
                decoded.allocation_size = word0 & 0x7u;
                decoded.allocation_unserialized = ((word1 >> 8) & 1u) != 0;
                decoded.allocation_type = (word1 >> 9) & 0x3u;
            }
            instructions.push_back(decoded);
        }
    }

    *output = std::move(instructions);
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_shader_fetch_instruction(
    const uint8_t* instruction_bytes,
    size_t byte_length,
    CapturedShaderFetchInstruction* output,
    std::string* error) {
    if (!instruction_bytes || !output || byte_length != 12) {
        return fail("captured shader fetch instruction must be 96 bits", error);
    }

    const uint32_t word0 = read_be32(instruction_bytes);
    const uint32_t word1 = read_be32(instruction_bytes + 4);
    const uint32_t word2 = read_be32(instruction_bytes + 8);
    const uint32_t opcode = word0 & 0x1Fu;
    CapturedShaderFetchInstruction decoded{};
    decoded.source_register = (word0 >> 5) & 0x3Fu;
    decoded.source_relative = ((word0 >> 11) & 1u) != 0;
    decoded.destination_register = (word0 >> 12) & 0x3Fu;
    decoded.destination_relative = ((word0 >> 18) & 1u) != 0;
    decoded.destination_swizzle = word1 & 0xFFFu;
    decoded.predicated = ((word1 >> 31) & 1u) != 0;
    decoded.predicate_condition = ((word2 >> 31) & 1u) != 0;

    if (opcode == 0) {
        if (((word1 >> 30) & 1u) != 0) {
            return fail("captured mini vertex fetch is unsupported", error);
        }
        decoded.kind = CapturedShaderFetchKind::VertexFull;
        decoded.fetch_constant_index =
            ((word0 >> 20) & 0x1Fu) * 3 + ((word0 >> 25) & 0x3u);
        decoded.source_swizzle = (word0 >> 30) & 0x3u;
        decoded.vertex_format = (word1 >> 16) & 0x3Fu;
        decoded.vertex_stride = word2 & 0xFFu;
        const uint32_t raw_offset = (word2 >> 8) & 0x7FFFFFu;
        decoded.vertex_offset = (raw_offset & 0x400000u)
                                    ? static_cast<int32_t>(
                                          static_cast<int64_t>(raw_offset) -
                                          (int64_t{1} << 23))
                                    : static_cast<int32_t>(raw_offset);
    } else if (opcode == 1) {
        decoded.kind = CapturedShaderFetchKind::Texture2D;
        decoded.fetch_constant_index = (word0 >> 20) & 0x1Fu;
        decoded.source_swizzle = (word0 >> 26) & 0x3Fu;
        decoded.texture_dimension = (word2 >> 14) & 0x3u;
        if (decoded.texture_dimension != 1) {
            return fail("captured texture fetch is not 2D", error);
        }
    } else {
        return fail("unsupported captured shader fetch opcode", error);
    }

    *output = decoded;
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_shader_alu_instruction(
    const uint8_t* instruction_bytes,
    size_t byte_length,
    CapturedShaderAluInstruction* output,
    std::string* error) {
    if (!instruction_bytes || !output || byte_length != 12) {
        return fail("captured shader ALU instruction must be 96 bits", error);
    }

    const uint32_t word0 = read_be32(instruction_bytes);
    const uint32_t word1 = read_be32(instruction_bytes + 4);
    const uint32_t word2 = read_be32(instruction_bytes + 8);
    CapturedShaderAluInstruction decoded{};
    decoded.vector_opcode = (word2 >> 24) & 0x1Fu;
    decoded.scalar_opcode = (word0 >> 26) & 0x3Fu;
    decoded.vector_destination = word0 & 0x3Fu;
    decoded.vector_destination_relative = ((word0 >> 6) & 1u) != 0;
    decoded.absolute_constants = ((word0 >> 7) & 1u) != 0;
    decoded.scalar_destination = (word0 >> 8) & 0x3Fu;
    decoded.scalar_destination_relative = ((word0 >> 14) & 1u) != 0;
    decoded.export_data = ((word0 >> 15) & 1u) != 0;
    decoded.vector_write_mask = (word0 >> 16) & 0xFu;
    decoded.scalar_write_mask = (word0 >> 20) & 0xFu;
    decoded.vector_clamp = ((word0 >> 24) & 1u) != 0;
    decoded.scalar_clamp = ((word0 >> 25) & 1u) != 0;
    decoded.predicated = ((word1 >> 28) & 1u) != 0;
    decoded.predicate_condition = ((word1 >> 27) & 1u) != 0;
    decoded.const_address_register_relative = ((word1 >> 29) & 1u) != 0;
    decoded.const1_relative = ((word1 >> 30) & 1u) != 0;
    decoded.const0_relative = ((word1 >> 31) & 1u) != 0;
    for (uint32_t source = 0; source < 3; ++source) {
        const uint32_t shift = 16 - source * 8;
        decoded.source_registers[source] = (word2 >> shift) & 0xFFu;
        decoded.source_swizzles[source] = (word1 >> shift) & 0xFFu;
        decoded.source_is_temporary[source] = ((word2 >> (31 - source)) & 1u) != 0;
        decoded.source_temporary_registers[source] =
            decoded.source_registers[source] & 0x3Fu;
        decoded.source_temporary_relative[source] =
            decoded.source_is_temporary[source] &&
            (decoded.source_registers[source] & 0x40u) != 0;
        decoded.source_temporary_absolute[source] =
            decoded.source_is_temporary[source] &&
            (decoded.source_registers[source] & 0x80u) != 0;
        decoded.source_negate[source] = ((word1 >> (26 - source)) & 1u) != 0;
    }
    decoded.scalar_temporary_register =
        (decoded.scalar_opcode & 1u) |
        (((word2 >> 29) & 1u) << 1) |
        (decoded.source_swizzles[2] & 0x3Cu);
    decoded.scalar_temporary_component = decoded.source_swizzles[2] & 0x3u;
    decoded.scalar_constant_component =
        (3u + ((decoded.source_swizzles[2] >> 6) & 0x3u)) & 0x3u;

    *output = decoded;
    if (error) {
        error->clear();
    }
    return true;
}

bool schedule_captured_shader_instructions(
    const std::vector<CapturedShaderControlFlow>& control_flow,
    size_t shader_byte_length,
    std::vector<CapturedShaderInstructionSchedule>* output,
    std::string* error) {
    constexpr size_t kInstructionBytes = 12;
    constexpr uint32_t kMaxSequenceInstructions = 6;
    if (!output || shader_byte_length == 0 ||
        (shader_byte_length % kInstructionBytes) != 0) {
        return fail("invalid captured shader schedule input", error);
    }

    const size_t instruction_count = shader_byte_length / kInstructionBytes;
    std::vector<CapturedShaderInstructionSchedule> scheduled;
    for (const CapturedShaderControlFlow& clause : control_flow) {
        if (clause.opcode != ShaderControlFlowOpcode::Exec &&
            clause.opcode != ShaderControlFlowOpcode::ExecEnd) {
            continue;
        }
        if (clause.instruction_count == 0 ||
            clause.instruction_count > kMaxSequenceInstructions ||
            static_cast<uint64_t>(clause.address) + clause.instruction_count >
                instruction_count) {
            return fail("captured shader exec clause is outside its instruction stream", error);
        }
        for (uint32_t offset = 0; offset < clause.instruction_count; ++offset) {
            const uint32_t sequence_bits = (clause.sequence >> (offset * 2)) & 0x3u;
            scheduled.push_back({
                clause.address + offset,
                clause.instruction_index,
                (sequence_bits & 1u) != 0 ? ShaderScheduledInstructionKind::Fetch
                                          : ShaderScheduledInstructionKind::Alu,
                (sequence_bits & 2u) != 0,
            });
        }
    }
    if (scheduled.empty()) {
        return fail("captured shader has no supported exec clauses", error);
    }

    *output = std::move(scheduled);
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_draw_indx(
    const uint8_t* packet_bytes,
    size_t byte_length,
    DecodedIndexedDraw* output,
    std::string* error) {
    if (!packet_bytes || !output || byte_length < kCapturedPacketBytes) {
        return fail("truncated PM4_DRAW_INDX packet", error);
    }

    const uint32_t header = read_be32(packet_bytes);
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kDrawIndxOpcode) {
        return fail("unsupported guest draw packet", error);
    }

    // The captured packet header encodes four payload dwords.
    const uint32_t payload_count = ((header & kPacketCountMask) >> 16) + 1;
    if (payload_count != 4 || byte_length != kCapturedPacketBytes) {
        return fail("unsupported PM4_DRAW_INDX payload length", error);
    }

    const uint32_t draw_initiator = read_be32(packet_bytes + 8);
    const uint32_t primitive_type = draw_initiator & 0x3Fu;
    const uint32_t source_select = (draw_initiator >> 6) & 0x3u;
    const uint32_t major_mode = (draw_initiator >> 8) & 0x3u;
    const uint32_t index_size = (draw_initiator >> 11) & 0x1u;
    const uint32_t initiator_index_count = draw_initiator >> 16;
    const uint32_t index_guest_address = read_be32(packet_bytes + 12);
    const uint32_t dma_size = read_be32(packet_bytes + 16);
    const uint32_t dma_index_count = dma_size & kIndexCountMask;
    const uint32_t dma_endian_mode = (dma_size & kDmaSwapModeMask) >> 30;

    if (primitive_type != kTriangleList) {
        return fail("unsupported captured primitive type", error);
    }
    if (source_select != 0 || major_mode != 0) {
        return fail("unsupported captured draw source or major mode", error);
    }
    if (index_size != 0 || dma_endian_mode != 1) {
        return fail("unsupported captured index format or endian mode", error);
    }
    if (!initiator_index_count || initiator_index_count != dma_index_count) {
        return fail("draw packet index counts disagree", error);
    }
    if ((dma_size & 0x3F000000u) != 0) {
        return fail("unsupported captured DMA size flags", error);
    }
    *output = DecodedIndexedDraw{
        PrimitiveTopology::TriangleList,
        initiator_index_count,
        index_guest_address,
        16,
        dma_endian_mode,
        dma_index_count * 2,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_vertex_fetch(
    const uint32_t descriptor_words[2],
    CapturedVertexFetch* output,
    std::string* error) {
    if (!descriptor_words || !output) {
        return fail("invalid captured vertex-fetch descriptor", error);
    }

    constexpr uint32_t kVertexFetchType = 3;
    constexpr uint32_t kCapturedVertexEndianMode = 2;
    const uint32_t fetch_type = descriptor_words[0] & 0x3u;
    const uint32_t endian_mode = descriptor_words[1] & 0x3u;
    const uint32_t size_words = (descriptor_words[1] >> 2) & 0x00FFFFFFu;
    if (fetch_type != kVertexFetchType || endian_mode != kCapturedVertexEndianMode ||
        size_words == 0) {
        return fail("unsupported captured vertex-fetch descriptor", error);
    }

    *output = CapturedVertexFetch{
        descriptor_words[0] & 0xFFFFFFFCu,
        endian_mode,
        size_words,
        size_words * 4,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_texture_fetch(
    const uint32_t descriptor_words[6],
    CapturedTextureFetch* output,
    std::string* error) {
    if (!descriptor_words || !output) {
        return fail("invalid captured texture-fetch descriptor", error);
    }

    const uint32_t fetch_type = descriptor_words[0] & 0x3u;
    const uint32_t tiled = descriptor_words[0] >> 31;
    const uint32_t format = descriptor_words[1] & 0x3Fu;
    const uint32_t endian_mode = (descriptor_words[1] >> 6) & 0x3u;
    const uint32_t stacked = (descriptor_words[1] >> 10) & 0x1u;
    const uint32_t width = (descriptor_words[2] & 0x1FFFu) + 1;
    const uint32_t height = ((descriptor_words[2] >> 13) & 0x1FFFu) + 1;
    const uint32_t stack_depth = descriptor_words[2] >> 26;
    const uint32_t mip_min = (descriptor_words[4] >> 2) & 0xFu;
    const uint32_t mip_max = (descriptor_words[4] >> 6) & 0xFu;
    const uint32_t dimension = (descriptor_words[5] >> 9) & 0x3u;

    if (fetch_type != 2 || format != 6 || endian_mode != 2 || !tiled || stacked ||
        stack_depth != 0 || dimension != 1 || mip_min != 0 || mip_max != 0) {
        return fail("unsupported captured texture-fetch descriptor", error);
    }

    const uint64_t byte_length = static_cast<uint64_t>(width) * height * 4;
    if (!width || !height || byte_length > std::numeric_limits<uint32_t>::max()) {
        return fail("captured texture dimensions are out of range", error);
    }

    *output = CapturedTextureFetch{
        ((descriptor_words[1] >> 12) & 0xFFFFFu) << 12,
        format,
        endian_mode,
        (descriptor_words[0] >> 2) & 0x3u,
        (descriptor_words[0] >> 4) & 0x3u,
        (descriptor_words[0] >> 6) & 0x3u,
        (descriptor_words[0] >> 8) & 0x3u,
        (descriptor_words[0] >> 10) & 0x7u,
        (descriptor_words[0] >> 13) & 0x7u,
        (descriptor_words[0] >> 16) & 0x7u,
        width,
        height,
        ((descriptor_words[0] >> 22) & 0x1FFu) << 5,
        static_cast<uint32_t>(byte_length),
        dimension,
        (descriptor_words[3] >> 1) & 0xFFFu,
        (descriptor_words[3] >> 19) & 0x3u,
        (descriptor_words[3] >> 21) & 0x3u,
        (descriptor_words[3] >> 23) & 0x3u,
        (descriptor_words[3] >> 25) & 0x7u,
        (descriptor_words[3] & 0x1u) != 0,
        descriptor_words[5] & 0x3u,
        (descriptor_words[3] >> 31) != 0,
        tiled != 0,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_texture_sampling(
    const CapturedTextureFetch& texture,
    CapturedTextureSampling* output,
    std::string* error) {
    if (!output) {
        return fail("invalid captured texture sampling output", error);
    }

    const uint32_t selectors[] = {
        texture.swizzle & 0x7u,
        (texture.swizzle >> 3) & 0x7u,
        (texture.swizzle >> 6) & 0x7u,
        (texture.swizzle >> 9) & 0x7u,
    };
    const uint32_t signs[] = {
        texture.sign_x, texture.sign_y, texture.sign_z, texture.sign_w,
    };
    const uint32_t clamps[] = {
        texture.clamp_x, texture.clamp_y, texture.clamp_z,
    };
    const uint32_t filters[] = {
        texture.mag_filter, texture.min_filter, texture.mip_filter,
    };
    for (uint32_t selector : selectors) {
        if (selector > static_cast<uint32_t>(TextureComponent::One)) {
            return fail("unsupported captured texture swizzle selector", error);
        }
    }
    for (uint32_t sign : signs) {
        if (sign > static_cast<uint32_t>(TextureSign::Gamma)) {
            return fail("unsupported captured texture channel sign", error);
        }
    }
    for (uint32_t clamp : clamps) {
        if (clamp > static_cast<uint32_t>(TextureClamp::MirrorClampToBorder)) {
            return fail("unsupported captured texture clamp mode", error);
        }
    }
    for (uint32_t filter : filters) {
        if (filter > static_cast<uint32_t>(TextureFilter::FetchConstant)) {
            return fail("unsupported captured texture filter", error);
        }
    }
    if (texture.aniso_filter == 6 || texture.aniso_filter > 7 ||
        texture.border_color > 3) {
        return fail("unsupported captured texture sampler field", error);
    }

    *output = CapturedTextureSampling{
        {static_cast<TextureComponent>(selectors[0]),
         static_cast<TextureComponent>(selectors[1]),
         static_cast<TextureComponent>(selectors[2]),
         static_cast<TextureComponent>(selectors[3])},
        {static_cast<TextureSign>(signs[0]),
         static_cast<TextureSign>(signs[1]),
         static_cast<TextureSign>(signs[2]),
         static_cast<TextureSign>(signs[3])},
        {static_cast<TextureClamp>(clamps[0]),
         static_cast<TextureClamp>(clamps[1]),
         static_cast<TextureClamp>(clamps[2])},
        static_cast<TextureFilter>(filters[0]),
        static_cast<TextureFilter>(filters[1]),
        static_cast<TextureFilter>(filters[2]),
        static_cast<TextureAnisotropy>(texture.aniso_filter),
        static_cast<TextureBorderColor>(texture.border_color),
        texture.border_color == 1,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_raster_state(
    const CapturedRasterRegisters& registers,
    CapturedRasterState* output,
    std::string* error) {
    if (!output) {
        return fail("invalid captured raster-state output", error);
    }

    const uint32_t surface_pitch = registers.surface_info & 0x3FFFu;
    const uint32_t msaa_samples = (registers.surface_info >> 16) & 0x3u;
    const uint32_t color_format = (registers.color_info >> 16) & 0xFu;
    const uint32_t depth_format = (registers.depth_info >> 16) & 0x1u;
    if (registers.mode_control != 4 || msaa_samples != 0 ||
        color_format != 1 || depth_format != 0 ||
        (registers.color_info & ~0x000F0FFFu) != 0 ||
        (registers.depth_info & ~0x00010FFFu) != 0 ||
        (registers.color_mask & ~0xFu) != 0 || registers.window_offset != 0) {
        return fail("unsupported captured target or raster state", error);
    }

    const float x_scale = register_float(registers.viewport_x_scale);
    const float x_offset = register_float(registers.viewport_x_offset);
    const float y_scale = register_float(registers.viewport_y_scale);
    const float y_offset = register_float(registers.viewport_y_offset);
    uint32_t width = 0;
    uint32_t height = 0;
    if (!viewport_dimension(x_scale, &width) || !viewport_dimension(-y_scale, &height) ||
        x_offset != x_scale || y_offset != -y_scale || surface_pitch != width) {
        return fail("unsupported captured viewport or surface pitch", error);
    }

    // The screen scissor uses signed 15-bit coordinates. The window scissor
    // uses unsigned 14-bit coordinates and may add a signed offset. This
    // captured form has only non-negative screen bounds and a zero offset.
    constexpr uint32_t kScreenReservedOrNegative = 0xC000C000u;
    constexpr uint32_t kWindowTlReserved = 0x4000C000u;
    constexpr uint32_t kWindowBrReserved = 0xC000C000u;
    if ((registers.screen_scissor_tl & kScreenReservedOrNegative) != 0 ||
        (registers.screen_scissor_br & kScreenReservedOrNegative) != 0 ||
        (registers.window_scissor_tl & kWindowTlReserved) != 0 ||
        (registers.window_scissor_br & kWindowBrReserved) != 0) {
        return fail("unsupported captured scissor encoding", error);
    }

    uint32_t x0 = std::max(registers.screen_scissor_tl & 0x7FFFu,
                           registers.window_scissor_tl & 0x3FFFu);
    uint32_t y0 = std::max((registers.screen_scissor_tl >> 16) & 0x7FFFu,
                           (registers.window_scissor_tl >> 16) & 0x3FFFu);
    uint32_t x1 = std::min(registers.screen_scissor_br & 0x7FFFu,
                           registers.window_scissor_br & 0x3FFFu);
    uint32_t y1 = std::min((registers.screen_scissor_br >> 16) & 0x7FFFu,
                           (registers.window_scissor_br >> 16) & 0x3FFFu);
    x0 = std::min(x0, width);
    y0 = std::min(y0, height);
    x1 = std::max(x0, std::min(x1, width));
    y1 = std::max(y0, std::min(y1, height));

    *output = CapturedRasterState{
        width,
        height,
        1,
        registers.color_info & 0xFFFu,
        CapturedColorTargetFormat::Rgba8Gamma,
        registers.depth_info & 0xFFFu,
        CapturedDepthTargetFormat::D24S8,
        registers.color_mask & 0xFu,
        y_scale < 0.0f,
        ((registers.depth_control >> 1) & 1u) != 0,
        ((registers.depth_control >> 2) & 1u) != 0,
        (registers.depth_control & 1u) != 0,
        x0,
        y0,
        x1,
        y1,
        x1 > x0 && y1 > y0,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_shader_constants(
    const uint32_t* float_bank_words,
    size_t float_word_count,
    const uint32_t* bool_bank_words,
    size_t bool_word_count,
    uint32_t vertex_constant_control,
    uint32_t pixel_constant_control,
    CapturedShaderConstants* output,
    std::string* error) {
    constexpr size_t kFloatBankWords = 512u * 4u;
    constexpr size_t kBoolBankWords = 8;
    constexpr uint32_t kControlReservedMask = 0xFFE00E00u;
    if (!float_bank_words || !bool_bank_words || !output ||
        float_word_count < kFloatBankWords || bool_word_count < kBoolBankWords) {
        return fail("truncated captured shader constant banks", error);
    }

    const auto valid_control = [](uint32_t control) {
        const uint32_t base = control & 0x1FFu;
        const uint32_t size = ((control >> 12) & 0x1FFu) + 1;
        return (control & kControlReservedMask) == 0 && size >= 256 &&
               base + size <= 512;
    };
    if (!valid_control(vertex_constant_control) ||
        !valid_control(pixel_constant_control)) {
        return fail("captured shader constant range does not cover required registers", error);
    }

    const uint32_t vertex_base = vertex_constant_control & 0x1FFu;
    const uint32_t pixel_base = pixel_constant_control & 0x1FFu;
    const auto read_float4 = [float_bank_words](uint32_t base, uint32_t index) {
        std::array<uint32_t, 4> value{};
        std::copy_n(float_bank_words + (base + index) * 4, 4, value.begin());
        return value;
    };

    CapturedShaderConstants decoded{};
    for (uint32_t i = 0; i < decoded.vertex_c64_to_c69.size(); ++i) {
        decoded.vertex_c64_to_c69[i] = read_float4(vertex_base, 64 + i);
    }
    decoded.vertex_c254 = read_float4(vertex_base, 254);
    decoded.vertex_c255 = read_float4(vertex_base, 255);
    decoded.pixel_c0 = read_float4(pixel_base, 0);
    decoded.pixel_c255 = read_float4(pixel_base, 255);
    decoded.pixel_b128 = (bool_bank_words[128 / 32] & (1u << (128 % 32))) != 0;
    decoded.pixel_b129 = (bool_bank_words[129 / 32] & (1u << (129 % 32))) != 0;
    *output = decoded;
    if (error) {
        error->clear();
    }
    return true;
}

bool untile_captured_texture_2d(
    const CapturedTextureFetch& texture,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error) {
    if (!guest_bytes || !vulkan_bytes || texture.format != 6 ||
        texture.endian_mode != 2 || texture.dimension != 1 || !texture.tiled ||
        !texture.width || !texture.height || texture.pitch != texture.width ||
        (texture.width & 31u) != 0 || (texture.height & 31u) != 0) {
        return fail("unsupported captured texture layout", error);
    }

    const uint64_t expected_bytes =
        static_cast<uint64_t>(texture.width) * texture.height * 4;
    if (expected_bytes > std::numeric_limits<uint32_t>::max() ||
        texture.byte_length != expected_bytes || byte_length != expected_bytes) {
        return fail("captured texture byte range does not match its dimensions", error);
    }

    std::vector<uint8_t> linear(static_cast<size_t>(expected_bytes));
    for (uint32_t y = 0; y < texture.height; ++y) {
        for (uint32_t x = 0; x < texture.width; ++x) {
            const size_t source = static_cast<size_t>(
                tiled_2d_offset_32bpp(x, y, texture.pitch));
            const size_t destination =
                (static_cast<size_t>(y) * texture.width + x) * 4;
            if (source + 4 > byte_length) {
                return fail("captured tiled texture address exceeds its byte range", error);
            }
            linear[destination] = guest_bytes[source + 3];
            linear[destination + 1] = guest_bytes[source + 2];
            linear[destination + 2] = guest_bytes[source + 1];
            linear[destination + 3] = guest_bytes[source];
        }
    }

    *vulkan_bytes = std::move(linear);
    if (error) {
        error->clear();
    }
    return true;
}

bool normalize_captured_buffer_bytes(
    uint32_t endian_mode,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error) {
    if (!guest_bytes || !vulkan_bytes || byte_length == 0) {
        return fail("invalid captured resource bytes", error);
    }

    const size_t word_bytes = endian_mode == 1 ? 2 : endian_mode == 2 ? 4 : 0;
    if (word_bytes == 0) {
        return fail("unsupported captured resource endian mode", error);
    }
    if (byte_length % word_bytes != 0) {
        return fail("captured resource length is not endian-word aligned", error);
    }

    std::vector<uint8_t> normalized(byte_length);
    for (size_t offset = 0; offset < byte_length; offset += word_bytes) {
        for (size_t byte = 0; byte < word_bytes; ++byte) {
            normalized[offset + byte] = guest_bytes[offset + word_bytes - byte - 1];
        }
    }
    *vulkan_bytes = std::move(normalized);
    if (error) {
        error->clear();
    }
    return true;
}

}  // namespace shift::xbox
