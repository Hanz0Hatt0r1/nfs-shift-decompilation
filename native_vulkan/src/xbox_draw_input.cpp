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
constexpr uint32_t kDrawIndx2Opcode = 0x36u;
constexpr uint32_t kInterruptOpcode = 0x54u;
constexpr uint32_t kImLoadOpcode = 0x27u;
constexpr uint32_t kImLoadImmediateOpcode = 0x2Bu;
constexpr uint32_t kLoadAluConstantOpcode = 0x2Fu;
constexpr uint32_t kIndirectBufferOpcode = 0x3Fu;
constexpr uint32_t kXeSwapOpcode = 0x64u;
constexpr uint32_t kXeSwapSignature = 0x53574150u;  // Big-endian "SWAP".
constexpr uint32_t kTriangleList = 4u;
constexpr uint32_t kIndexCountMask = 0x00FFFFFFu;
constexpr uint32_t kDmaSwapModeMask = 0xC0000000u;
constexpr size_t kMinimumDrawPacketBytes = 4;

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

uint64_t tiled_2d_offset_16bpb(uint32_t x, uint32_t y, uint32_t pitch_blocks) {
    const uint64_t macro =
        ((static_cast<uint64_t>(x >> 5) +
          static_cast<uint64_t>(y >> 5) * (pitch_blocks >> 5)) << 11);
    const uint64_t micro =
        (static_cast<uint64_t>((x & 7u) + ((y & 0xEu) << 2)) << 4);
    const uint64_t offset = macro + ((micro & ~uint64_t{0xFu}) << 1) +
                            (micro & 0xFu) + (static_cast<uint64_t>(y & 1u) << 4);
    return ((offset & ~uint64_t{0x1FFu}) << 3) +
           (static_cast<uint64_t>(y & 0x10u) << 7) +
           ((offset & 0x1C0u) << 2) +
           (((((y & 8u) >> 2) + (x >> 3)) & 3u) << 6) +
           (offset & 0x3Fu);
}

uint64_t tiled_2d_offset_8bpb(uint32_t x, uint32_t y, uint32_t pitch_blocks) {
    const uint64_t outer_blocks =
        ((static_cast<uint64_t>(x >> 5) +
          static_cast<uint64_t>(y >> 5) * (pitch_blocks >> 5)) << 6);
    const uint64_t inner_blocks = (((y >> 1) & 0x7u) << 3) | (x & 0x7u);
    const uint64_t outer_inner_bytes = (outer_blocks | inner_blocks) << 3;
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

uint64_t compressed_texture_storage_bytes(uint32_t pitch_pixels, uint32_t height,
                                          uint32_t bytes_per_block, bool tiled) {
    const uint64_t blocks_wide = pitch_pixels / 4u;
    const uint64_t blocks_high = (height + 3u) / 4u;
    if (!tiled) return blocks_wide * blocks_high * bytes_per_block;
    // Xenos tiled compressed subresources allocate complete 32x32 block tiles.
    const uint64_t tiles_wide = (blocks_wide + 31u) / 32u;
    const uint64_t tiles_high = (blocks_high + 31u) / 32u;
    return tiles_wide * tiles_high * 32u * 32u * bytes_per_block;
}

uint64_t tiled_rgba8_storage_bytes(uint32_t pitch_pixels, uint32_t height) {
    const uint64_t tile_rows = (static_cast<uint64_t>(height) + 31u) / 32u;
    return static_cast<uint64_t>(pitch_pixels) * tile_rows * 32u * 4u;
}

struct Dxt5AlphaBlock {
    std::array<uint8_t, 8> values{};
    uint64_t indices = 0;
};

Dxt5AlphaBlock decode_dxt5_alpha_block(const uint8_t* block) {
    Dxt5AlphaBlock decoded{};
    decoded.values[0] = block[0];
    decoded.values[1] = block[1];
    if (decoded.values[0] > decoded.values[1]) {
        for (uint32_t i = 2; i < 8; ++i) {
            decoded.values[i] = static_cast<uint8_t>(
                ((8u - i) * decoded.values[0] +
                 (i - 1u) * decoded.values[1]) / 7u);
        }
    } else {
        for (uint32_t i = 2; i < 6; ++i) {
            decoded.values[i] = static_cast<uint8_t>(
                ((6u - i) * decoded.values[0] +
                 (i - 1u) * decoded.values[1]) / 5u);
        }
        decoded.values[6] = 0;
        decoded.values[7] = 255;
    }
    for (uint32_t i = 0; i < 6; ++i) {
        decoded.indices |= static_cast<uint64_t>(block[2u + i]) << (i * 8u);
    }
    return decoded;
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

bool decode_guest_register_writes(
    const uint8_t* packet_bytes,
    size_t byte_length,
    std::vector<GuestRegisterWrite>* output,
    std::string* error) {
    if (!packet_bytes || !output || byte_length < 4u || (byte_length & 3u) != 0u) {
        return fail("invalid PM4 register-write packet input", error);
    }

    const uint32_t header = read_be32(packet_bytes);
    const uint32_t packet_type = header >> 30;
    std::vector<GuestRegisterWrite> writes;
    if (packet_type == 0u) {
        const uint32_t value_count = ((header >> 16) & 0x3FFFu) + 1u;
        if (byte_length != (static_cast<size_t>(value_count) + 1u) * 4u) {
            return fail("type-0 PM4 packet size mismatch", error);
        }
        const uint32_t base_index = header & 0x7FFFu;
        const bool write_one_register = ((header >> 15) & 1u) != 0u;
        writes.reserve(value_count);
        for (uint32_t index = 0; index < value_count; ++index) {
            writes.push_back(GuestRegisterWrite{
                write_one_register ? base_index : base_index + index,
                read_be32(packet_bytes + 4u + static_cast<size_t>(index) * 4u),
            });
        }
    } else if (packet_type == 1u) {
        if (byte_length != 12u) {
            return fail("type-1 PM4 packet size mismatch", error);
        }
        writes.push_back(GuestRegisterWrite{
            header & 0x7FFu,
            read_be32(packet_bytes + 4u),
        });
        writes.push_back(GuestRegisterWrite{
            (header >> 11) & 0x7FFu,
            read_be32(packet_bytes + 8u),
        });
    } else {
        return fail("PM4 packet does not contain register writes", error);
    }

    *output = std::move(writes);
    if (error) error->clear();
    return true;
}

bool decode_captured_shader_program_load(
    const uint8_t* packet_bytes,
    size_t byte_length,
    CapturedShaderProgramLoad* output,
    std::string* error) {
    if (!packet_bytes || !output || byte_length != 3u * sizeof(uint32_t)) {
        return fail("invalid captured PM4_IM_LOAD packet", error);
    }
    const uint32_t header = read_be32(packet_bytes);
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kImLoadOpcode ||
        ((header & kPacketCountMask) >> 16) != 1u) {
        return fail("unsupported captured PM4_IM_LOAD packet form", error);
    }

    const uint32_t address_and_stage = read_be32(packet_bytes + 4);
    const uint32_t start_and_size = read_be32(packet_bytes + 8);
    const uint32_t stage = address_and_stage & 0x3u;
    const uint32_t dword_count = start_and_size & 0xFFFFu;
    if (stage > 1u || (start_and_size >> 16) != 0u || dword_count == 0u) {
        return fail("unsupported captured shader stage or program span", error);
    }

    *output = CapturedShaderProgramLoad{
        stage == 0u ? GuestShaderStage::Vertex : GuestShaderStage::Pixel,
        address_and_stage & ~0x3u,
        dword_count,
        dword_count * static_cast<uint32_t>(sizeof(uint32_t)),
    };
    if (error) error->clear();
    return true;
}

bool decode_captured_immediate_shader_program_load(
    const uint8_t* packet_bytes,
    size_t byte_length,
    CapturedImmediateShaderProgramLoad* output,
    std::string* error) {
    if (!packet_bytes || !output || byte_length < 4u * sizeof(uint32_t) ||
        (byte_length & 3u) != 0u) {
        return fail("invalid PM4_IM_LOAD_IMMEDIATE packet", error);
    }

    const uint32_t header = read_be32(packet_bytes);
    const uint32_t payload_count = ((header & kPacketCountMask) >> 16) + 1u;
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kImLoadImmediateOpcode ||
        payload_count < 3u || byte_length != (payload_count + 1u) * sizeof(uint32_t)) {
        return fail("unsupported PM4_IM_LOAD_IMMEDIATE packet form", error);
    }

    const uint32_t stage = read_be32(packet_bytes + 4u);
    const uint32_t start_and_size = read_be32(packet_bytes + 8u);
    const uint32_t start = start_and_size >> 16;
    const uint32_t dword_count = start_and_size & 0xFFFFu;
    if (stage > 1u || start != 0u || dword_count == 0u ||
        static_cast<uint64_t>(dword_count) + 2u > payload_count) {
        return fail("invalid inline shader stage or program span", error);
    }

    *output = CapturedImmediateShaderProgramLoad{
        stage == 0u ? GuestShaderStage::Vertex : GuestShaderStage::Pixel,
        dword_count,
        dword_count * static_cast<uint32_t>(sizeof(uint32_t)),
        3u * sizeof(uint32_t),
    };
    if (error) error->clear();
    return true;
}

bool decode_captured_constant_load(
    const uint8_t* packet_bytes,
    size_t byte_length,
    CapturedConstantLoad* output,
    std::string* error) {
    constexpr uint32_t kAllowedOffsetTypeBits = 0x00FF07FFu;
    constexpr uint32_t kSizeMask = 0x00000FFFu;
    if (!packet_bytes || !output || byte_length != 4u * sizeof(uint32_t)) {
        return fail("invalid captured PM4_LOAD_ALU_CONSTANT packet", error);
    }
    const uint32_t header = read_be32(packet_bytes);
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kLoadAluConstantOpcode ||
        ((header & kPacketCountMask) >> 16) != 2u) {
        return fail("unsupported captured PM4_LOAD_ALU_CONSTANT form", error);
    }

    const uint32_t guest_address = read_be32(packet_bytes + 4) & 0x3FFFFFFFu;
    const uint32_t offset_type = read_be32(packet_bytes + 8);
    const uint32_t size = read_be32(packet_bytes + 12);
    const uint32_t bank_type = (offset_type >> 16) & 0xFFu;
    const uint32_t start_index = offset_type & 0x7FFu;
    const uint32_t dword_count = size & kSizeMask;
    if ((offset_type & ~kAllowedOffsetTypeBits) != 0 ||
        (size & ~kSizeMask) != 0 || (guest_address & 3u) != 0 ||
        dword_count == 0) {
        return fail("invalid captured constant-load address or range", error);
    }

    CapturedConstantBank bank{};
    uint32_t register_base = 0;
    uint32_t bank_dword_limit = 0;
    switch (bank_type) {
        case 0: bank = CapturedConstantBank::Alu; register_base = 0x4000; bank_dword_limit = 0x800; break;
        case 1: bank = CapturedConstantBank::Fetch; register_base = 0x4800; bank_dword_limit = 0x100; break;
        case 2: bank = CapturedConstantBank::Boolean; register_base = 0x4900; bank_dword_limit = 8; break;
        case 3: bank = CapturedConstantBank::Loop; register_base = 0x4908; bank_dword_limit = 0x20; break;
        case 4: bank = CapturedConstantBank::Registers; register_base = 0x2000; bank_dword_limit = 0x800; break;
        default: return fail("unsupported captured constant-load bank", error);
    }
    if (static_cast<uint64_t>(start_index) + dword_count > bank_dword_limit) {
        return fail("captured constant-load range exceeds its bank", error);
    }

    *output = CapturedConstantLoad{
        bank,
        guest_address,
        start_index,
        dword_count,
        register_base + start_index,
        dword_count * static_cast<uint32_t>(sizeof(uint32_t)),
    };
    if (error) error->clear();
    return true;
}

bool decode_captured_constant_load_data(
    const CapturedConstantLoad& load,
    const uint8_t* source_bytes,
    size_t byte_length,
    std::vector<GuestRegisterWrite>* output,
    std::string* error) {
    uint32_t register_base = 0;
    uint32_t bank_limit = 0;
    switch (load.bank) {
        case CapturedConstantBank::Alu: register_base = 0x4000; bank_limit = 0x800; break;
        case CapturedConstantBank::Fetch: register_base = 0x4800; bank_limit = 0x100; break;
        case CapturedConstantBank::Boolean: register_base = 0x4900; bank_limit = 8; break;
        case CapturedConstantBank::Loop: register_base = 0x4908; bank_limit = 0x20; break;
        case CapturedConstantBank::Registers: register_base = 0x2000; bank_limit = 0x800; break;
        default: return fail("invalid captured constant-load bank", error);
    }
    if (!source_bytes || !output || load.dword_count == 0 ||
        static_cast<uint64_t>(load.start_index) + load.dword_count > bank_limit ||
        load.destination_register != register_base + load.start_index ||
        load.byte_length != load.dword_count * sizeof(uint32_t) ||
        load.byte_length > 0x2000u || byte_length != load.byte_length) {
        return fail("invalid captured constant-load source span", error);
    }
    std::vector<GuestRegisterWrite> writes;
    writes.reserve(load.dword_count);
    for (uint32_t i = 0; i < load.dword_count; ++i) {
        writes.push_back({load.destination_register + i,
                          read_be32(source_bytes + static_cast<size_t>(i) * 4)});
    }
    *output = std::move(writes);
    if (error) error->clear();
    return true;
}

bool decode_captured_indirect_buffer(
    const uint8_t* packet_bytes,
    size_t byte_length,
    CapturedIndirectBuffer* output,
    std::string* error) {
    constexpr size_t kPacketBytes = 3u * sizeof(uint32_t);
    constexpr uint32_t kAddressMask = 0xFFFFFFFFu;
    constexpr uint32_t kLengthMask = 0x000FFFFFu;
    if (!packet_bytes || !output || byte_length != kPacketBytes) {
        return fail("invalid captured PM4_INDIRECT_BUFFER packet size", error);
    }

    const uint32_t header = read_be32(packet_bytes);
    const uint32_t payload_count = ((header & kPacketCountMask) >> 16) + 1u;
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kIndirectBufferOpcode ||
        payload_count != 2u) {
        return fail("unsupported captured PM4_INDIRECT_BUFFER form", error);
    }

    const uint32_t guest_address = read_be32(packet_bytes + 4u) & kAddressMask;
    const uint32_t length = read_be32(packet_bytes + 8u);
    if ((guest_address & 3u) != 0u || length == 0u ||
        (length & ~kLengthMask) != 0u ||
        static_cast<uint64_t>(guest_address) +
                static_cast<uint64_t>(length) * sizeof(uint32_t) >
            (uint64_t{1} << 32)) {
        return fail("invalid captured PM4_INDIRECT_BUFFER guest span", error);
    }

    *output = CapturedIndirectBuffer{guest_address, length};
    if (error) error->clear();
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
        const bool mini_fetch = ((word1 >> 30) & 1u) != 0;
        decoded.kind = mini_fetch ? CapturedShaderFetchKind::VertexMini
                                  : CapturedShaderFetchKind::VertexFull;
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

bool inherit_captured_vertex_fetch_fields(
    const CapturedShaderFetchInstruction& instruction,
    const CapturedShaderFetchInstruction* preceding_full_fetch,
    CapturedShaderFetchInstruction* output,
    std::string* error) {
    if (!output) {
        return fail("invalid captured vertex-fetch inheritance output", error);
    }
    if (instruction.kind == CapturedShaderFetchKind::VertexFull) {
        *output = instruction;
    } else if (instruction.kind == CapturedShaderFetchKind::VertexMini) {
        if (!preceding_full_fetch ||
            preceding_full_fetch->kind != CapturedShaderFetchKind::VertexFull) {
            return fail("captured mini vertex fetch has no preceding full fetch", error);
        }
        CapturedShaderFetchInstruction resolved = instruction;
        resolved.source_register = preceding_full_fetch->source_register;
        resolved.source_relative = preceding_full_fetch->source_relative;
        resolved.source_swizzle = preceding_full_fetch->source_swizzle;
        resolved.fetch_constant_index = preceding_full_fetch->fetch_constant_index;
        resolved.vertex_stride = preceding_full_fetch->vertex_stride;
        *output = resolved;
    } else {
        return fail("captured shader fetch is not a vertex fetch", error);
    }
    if (error) error->clear();
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
    if (!packet_bytes || !output || byte_length < kMinimumDrawPacketBytes) {
        return fail("truncated draw PM4 packet", error);
    }

    const uint32_t header = read_be32(packet_bytes);
    const uint32_t opcode = (header & kPacketOpcodeMask) >> 8;
    const bool has_viz_query = opcode == kDrawIndxOpcode;
    if ((header & kPacketTypeMask) != kType3Header ||
        (!has_viz_query && opcode != kDrawIndx2Opcode)) {
        return fail("unsupported guest draw packet", error);
    }

    const uint32_t payload_count = ((header & kPacketCountMask) >> 16) + 1;
    const size_t packet_byte_length = (payload_count + 1u) * sizeof(uint32_t);
    if (byte_length != packet_byte_length) {
        return fail("draw PM4 packet length disagrees with its header", error);
    }

    const size_t initiator_offset = has_viz_query ? 8u : 4u;
    if (payload_count < (has_viz_query ? 2u : 1u)) {
        return fail("draw PM4 packet has no complete initiator", error);
    }
    const uint32_t draw_initiator = read_be32(packet_bytes + initiator_offset);
    const uint32_t source_select = (draw_initiator >> 6) & 0x3u;
    const uint32_t primitive_type = draw_initiator & 0x3Fu;
    const uint32_t major_mode = (draw_initiator >> 8) & 0x3u;
    const uint32_t index_size = (draw_initiator >> 11) & 0x1u;
    const uint32_t initiator_index_count = draw_initiator >> 16;
    if (source_select == 1u) {
      return fail("unsupported immediate-index draw source", error);
    }
    if (source_select == 2u) {
      const uint32_t expected_payload_count = has_viz_query ? 2u : 1u;
      if (payload_count != expected_payload_count || major_mode != 0u ||
          index_size != 0u || initiator_index_count == 0u) {
        return fail(has_viz_query ? "unsupported AutoIndex DRAW_INDX form"
                                  : "unsupported AutoIndex DRAW_INDX_2 form",
                    error);
      }
      PrimitiveTopology topology{};
      if (primitive_type == 1u) {
        topology = PrimitiveTopology::PointList;
      } else if (primitive_type == kTriangleList &&
                 initiator_index_count % 3u == 0u) {
        topology = PrimitiveTopology::TriangleList;
      } else if (primitive_type == 6u && initiator_index_count >= 3u) {
        topology = PrimitiveTopology::TriangleStrip;
      } else if (primitive_type == 8u && initiator_index_count % 3u == 0u) {
        topology = PrimitiveTopology::RectangleList;
      } else {
        if (error) {
          *error = "unsupported AutoIndex primitive type " +
                   std::to_string(primitive_type) + " count " +
                   std::to_string(initiator_index_count);
        }
        return false;
      }
      *output = DecodedIndexedDraw{
          topology, initiator_index_count, 0, 0, 0, 0, true};
      if (error) error->clear();
      return true;
    }
    if (source_select != 0u) {
        return fail("unsupported captured draw source", error);
    }

    const uint32_t expected_payload_count = has_viz_query ? 4u : 3u;
    if (payload_count != expected_payload_count) {
      return fail("unsupported indexed draw PM4 payload length", error);
    }

    const uint32_t index_guest_address = read_be32(packet_bytes + initiator_offset + 4u);
    const uint32_t dma_size = read_be32(packet_bytes + initiator_offset + 8u);
    const uint32_t dma_index_count = dma_size & kIndexCountMask;
    const uint32_t dma_endian_mode = (dma_size & kDmaSwapModeMask) >> 30;

    if (primitive_type != kTriangleList) {
        return fail("unsupported captured primitive type", error);
    }
    if (major_mode != 0) {
        return fail("unsupported captured draw major mode", error);
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

bool decode_captured_gpu_interrupt(
    const uint8_t* packet_bytes,
    size_t byte_length,
    uint32_t* cpu_mask,
    std::string* error) {
    if (!packet_bytes || !cpu_mask || byte_length < 8u) {
        return fail("invalid PM4_INTERRUPT packet input", error);
    }
    const uint32_t header = read_be32(packet_bytes);
    const size_t expected_bytes =
        (static_cast<size_t>((header >> 16) & 0x3FFFu) + 2u) * sizeof(uint32_t);
    if ((header >> 30) != 3u ||
        ((header & kPacketOpcodeMask) >> 8) != kInterruptOpcode ||
        byte_length != expected_bytes) {
        return fail("unsupported PM4_INTERRUPT packet form", error);
    }
    *cpu_mask = read_be32(packet_bytes + sizeof(uint32_t));
    if (error) error->clear();
    return true;
}

bool decode_guest_swap(
    const uint8_t* packet_bytes,
    size_t byte_length,
    DecodedGuestSwap* output,
    std::string* error) {
    constexpr size_t kPacketBytes = 5u * sizeof(uint32_t);
    constexpr uint32_t kPhysicalAddressMask = 0x1FFFFFFFu;
    if (!packet_bytes || !output || byte_length != kPacketBytes) {
        return fail("invalid PM4_XE_SWAP packet size", error);
    }
    const uint32_t header = read_be32(packet_bytes);
    const uint32_t payload_count = ((header & kPacketCountMask) >> 16) + 1u;
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kXeSwapOpcode || payload_count != 4u ||
        read_be32(packet_bytes + 4u) != kXeSwapSignature) {
        return fail("unsupported PM4_XE_SWAP signature or packet form", error);
    }

    const uint32_t address = read_be32(packet_bytes + 8u);
    const uint32_t width = read_be32(packet_bytes + 12u);
    const uint32_t height = read_be32(packet_bytes + 16u);
    if ((address & ~kPhysicalAddressMask) != 0u || (address & 0xFFFu) != 0u ||
        width == 0u || height == 0u || width > 16384u || height > 16384u ||
        static_cast<uint64_t>(width) * height > (uint64_t{1} << 27)) {
        return fail("invalid PM4_XE_SWAP frontbuffer span", error);
    }

    *output = DecodedGuestSwap{address, width, height};
    if (error) error->clear();
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
    const uint32_t pitch = ((descriptor_words[0] >> 22) & 0x1FFu) << 5;
    const uint32_t base_address =
        ((descriptor_words[1] >> 12) & 0xFFFFFu) << 12;
    const uint32_t mip_address =
        ((descriptor_words[5] >> 12) & 0xFFFFFu) << 12;

    const bool r8 = format == 2 && endian_mode == 0;
    const bool rgba8 = format == 6 && endian_mode == 2;
    const bool dxt = (format == 19 || format == 20) && endian_mode == 1;
    const bool dxt5a = format == 59 && endian_mode == 1;
    const bool compressed = dxt || dxt5a;
    const bool valid_texture_layout = r8
        ? !tiled && pitch >= width
        : rgba8 ? tiled && pitch >= width && pitch % 32u == 0
                : compressed && width % 4u == 0 && height % 4u == 0 &&
                      pitch >= width && pitch % 4u == 0 &&
                      (!tiled || pitch % 128u == 0);
    // A mip range with the same nonzero base and mip page has no separate
    // mip payload. Preserve the one captured base level; distinct mip pages
    // and packed tails with separate storage need subresource upload support.
    const bool mip_range_aliases_base = mip_max != 0 && mip_min == 0 &&
        base_address != 0 && base_address == mip_address;
    if (fetch_type != 2 || !valid_texture_layout || stacked || stack_depth != 0 ||
        dimension != 1 || mip_min != 0 || (mip_max != 0 && !mip_range_aliases_base)) {
        return fail("unsupported captured texture-fetch descriptor", error);
    }

    const uint64_t byte_length = r8
        ? static_cast<uint64_t>(pitch) * height
        : rgba8 ? tiled_rgba8_storage_bytes(pitch, height)
                : compressed_texture_storage_bytes(
                      pitch, height, dxt5a ? 8u : 16u, tiled != 0);
    if (!width || !height || byte_length > std::numeric_limits<uint32_t>::max()) {
        return fail("captured texture dimensions are out of range", error);
    }

    *output = CapturedTextureFetch{
        base_address,
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
        pitch,
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

void GuestRasterRegisterState::reset() noexcept {
    registers_ = {};
    valid_mask_ = 0;
    viewport_transform_valid_mask_ = 0;
}

void GuestRasterRegisterState::apply(const GuestRegisterWrite& write) noexcept {
    if (write.register_index == 0x210Du) {
        registers_.stencil_refmask = write.value;
        return;
    }
    switch (write.register_index) {
        case 0x2318u:
            registers_.copy_control = write.value;
            registers_.copy_valid_mask |= 1u;
            return;
        case 0x2319u:
            registers_.copy_dest_base = write.value;
            registers_.copy_valid_mask |= 2u;
            return;
        case 0x231Au:
            registers_.copy_dest_pitch = write.value;
            registers_.copy_valid_mask |= 4u;
            return;
        case 0x231Bu:
            registers_.copy_dest_info = write.value;
            registers_.copy_valid_mask |= 8u;
            return;
        default:
            break;
    }
    uint32_t bit = 0;
    uint32_t* destination = nullptr;
    if (write.register_index == 0x2204u) {
        registers_.clip_control = write.value;
        viewport_transform_valid_mask_ |= 1u;
        registers_.viewport_transform_valid_mask = viewport_transform_valid_mask_;
        return;
    }
    if (write.register_index == 0x2206u) {
        registers_.viewport_transform_control = write.value;
        viewport_transform_valid_mask_ |= 2u;
        registers_.viewport_transform_valid_mask = viewport_transform_valid_mask_;
        return;
    }
    switch (write.register_index) {
        case 0x2000: bit = 1u << 0; destination = &registers_.surface_info; break;
        case 0x2001: bit = 1u << 1; destination = &registers_.color_info; break;
        case 0x2002: bit = 1u << 2; destination = &registers_.depth_info; break;
        case 0x2208: bit = 1u << 3; destination = &registers_.mode_control; break;
        case 0x2200: bit = 1u << 4; destination = &registers_.depth_control; break;
        case 0x2104: bit = 1u << 5; destination = &registers_.color_mask; break;
        case 0x210F: bit = 1u << 6; destination = &registers_.viewport_x_scale; break;
        case 0x2110: bit = 1u << 7; destination = &registers_.viewport_x_offset; break;
        case 0x2111: bit = 1u << 8; destination = &registers_.viewport_y_scale; break;
        case 0x2112: bit = 1u << 9; destination = &registers_.viewport_y_offset; break;
        case 0x200E: bit = 1u << 10; destination = &registers_.screen_scissor_tl; break;
        case 0x200F: bit = 1u << 11; destination = &registers_.screen_scissor_br; break;
        case 0x2080: bit = 1u << 12; destination = &registers_.window_offset; break;
        case 0x2081: bit = 1u << 13; destination = &registers_.window_scissor_tl; break;
        case 0x2082: bit = 1u << 14; destination = &registers_.window_scissor_br; break;
        case 0x2201: bit = 1u << 15; destination = &registers_.blend_control_0; break;
        case 0x2205: bit = 1u << 16; destination = &registers_.setup_mode_control; break;
        default: return;
    }
    *destination = write.value;
    valid_mask_ |= bit;
}

bool GuestRasterRegisterState::snapshot(
    CapturedRasterRegisters* output,
    std::string* error) const {
    constexpr uint32_t kAllRasterRegistersValid = (1u << 17) - 1u;
    if (!output || valid_mask_ != kAllRasterRegistersValid) {
        return fail("incomplete captured raster register state", error);
    }
    *output = registers_;
    if (error) error->clear();
    return true;
}

uint32_t GuestRasterRegisterState::observed_register_mask() const noexcept {
    return valid_mask_;
}

void CapturedXboxShaderRegisterState::reset() noexcept {
    *this = CapturedXboxShaderRegisterState{};
}

void CapturedXboxShaderRegisterState::apply(const GuestRegisterWrite& write) noexcept {
    const uint32_t index = write.register_index;
    if (index >= 0x4000u && index < 0x4800u) {
        const size_t slot = index - 0x4000u;
        float_words_[slot] = write.value;
        float_valid_[slot] = true;
    } else if (index >= 0x4800u && index < 0x4900u) {
        const size_t slot = index - 0x4800u;
        fetch_words_[slot] = write.value;
        fetch_valid_[slot] = true;
    } else if (index >= 0x4900u && index < 0x4908u) {
        const size_t slot = index - 0x4900u;
        bool_words_[slot] = write.value;
        bool_valid_[slot] = true;
    } else if (index == 0x2307u) {
        vertex_control_ = write.value;
        vertex_control_valid_ = true;
    } else if (index == 0x2308u) {
        pixel_control_ = write.value;
        pixel_control_valid_ = true;
    }
}

bool CapturedXboxShaderRegisterState::snapshot(
    CapturedShaderConstants* constants,
    std::array<uint32_t, 2>* vertex_descriptor,
    std::array<uint32_t, 6>* texture_descriptor,
    std::string* error) const {
    if (!constants || !vertex_descriptor || !texture_descriptor) {
        return fail("invalid captured shader register snapshot output", error);
    }
    if (!snapshot_constants(constants, error) ||
        !snapshot_vertex_fetch_descriptor(95, vertex_descriptor, error) ||
        !snapshot_texture_fetch_descriptor(0, texture_descriptor, error)) {
        return false;
    }
    if (error) error->clear();
    return true;
}

bool CapturedXboxShaderRegisterState::snapshot_constants(
    CapturedShaderConstants* constants,
    std::string* error) const {
    if (!constants) {
        return fail("invalid captured shader constants snapshot output", error);
    }
    if (!vertex_control_valid_) {
        return fail("missing vertex shader control register 0x2307", error);
    }
    if (!pixel_control_valid_) {
        return fail("missing pixel shader control register 0x2308", error);
    }
    if (vertex_control_ != 0x000FF000u) {
        return fail("unsupported vertex shader control value", error);
    }
    if (pixel_control_ != 0x000FF100u) {
        return fail("unsupported pixel shader control value", error);
    }
    CapturedShaderConstants decoded{};
    if (!decode_captured_shader_constants(
            float_words_.data(), float_words_.size(), bool_words_.data(),
            bool_words_.size(), vertex_control_, pixel_control_, &decoded, error)) {
        return false;
    }
    decoded.pixel_boolean_constants_valid = bool_valid_[4];
    *constants = decoded;
    if (error) error->clear();
    return true;
}

bool CapturedXboxShaderRegisterState::validate_float_constants(
    GuestShaderStage stage,
    const std::vector<uint32_t>& registers,
    bool relative_indexing,
    std::string* error) const {
    constexpr uint32_t kFloatRegistersPerStage = 256;
    const uint32_t first_register =
        stage == GuestShaderStage::Pixel ? kFloatRegistersPerStage : 0;
    const auto is_valid = [this, first_register](uint32_t index) {
        const size_t first = static_cast<size_t>(first_register + index) * 4;
        return float_valid_[first] && float_valid_[first + 1] &&
               float_valid_[first + 2] && float_valid_[first + 3];
    };
    if (relative_indexing) {
        for (uint32_t index = 0; index < kFloatRegistersPerStage; ++index) {
            if (!is_valid(index)) {
                if (error) {
                    *error = stage == GuestShaderStage::Vertex
                                 ? "captured vertex shader uses relative float constants "
                                   "with an incomplete constant window"
                                 : "captured pixel shader uses relative float constants "
                                   "with an incomplete constant window";
                }
                return false;
            }
        }
    }
    for (uint32_t index : registers) {
        if (index >= kFloatRegistersPerStage || !is_valid(index)) {
            if (error) {
                *error = stage == GuestShaderStage::Vertex
                             ? "captured vertex float constant " +
                                   std::to_string(index) + " is incomplete"
                             : "captured pixel float constant " +
                                   std::to_string(index) + " is incomplete";
            }
            return false;
        }
    }
    if (error) error->clear();
    return true;
}

bool CapturedXboxShaderRegisterState::snapshot_vertex_fetch_descriptor(
    uint32_t index,
    std::array<uint32_t, 2>* descriptor,
    std::string* error) const {
    constexpr uint32_t kMaxVertexFetchConstants = 96;
    const size_t first = static_cast<size_t>(index) * 2;
    if (!descriptor || index >= kMaxVertexFetchConstants ||
        first + 2 > fetch_words_.size()) {
        return fail("captured vertex fetch descriptor index is out of range", error);
    }
    if (!fetch_valid_[first] || !fetch_valid_[first + 1]) {
        return fail("captured vertex fetch descriptor is incomplete", error);
    }
    *descriptor = {fetch_words_[first], fetch_words_[first + 1]};
    if (error) error->clear();
    return true;
}

bool CapturedXboxShaderRegisterState::snapshot_texture_fetch_descriptor(
    uint32_t index,
    std::array<uint32_t, 6>* descriptor,
    std::string* error) const {
    constexpr uint32_t kMaxTextureFetchConstants = 32;
    const size_t first = static_cast<size_t>(index) * 6;
    if (!descriptor || index >= kMaxTextureFetchConstants ||
        first + 6 > fetch_words_.size()) {
        return fail("captured texture fetch descriptor index is out of range", error);
    }
    for (size_t word = 0; word < 6; ++word) {
        if (!fetch_valid_[first + word]) {
            return fail("captured texture fetch descriptor is incomplete", error);
        }
    }
    std::copy_n(fetch_words_.begin() + first, 6, descriptor->begin());
    if (error) error->clear();
    return true;
}

bool decode_captured_raster_state(
    const CapturedRasterRegisters& registers,
    CapturedRasterState* output,
    std::string* error,
    uint32_t target_width,
    uint32_t target_height) {
    if (!output) {
        return fail("invalid captured raster-state output", error);
    }

    const uint32_t surface_pitch = registers.surface_info & 0x3FFFu;
    const uint32_t msaa_samples = (registers.surface_info >> 16) & 0x3u;
    const uint32_t color_format = (registers.color_info >> 16) & 0xFu;
    const uint32_t depth_format = (registers.depth_info >> 16) & 0x1u;
    const bool depth_only = registers.mode_control == 5u;
    if ((registers.mode_control != 4u && !depth_only) || msaa_samples > 2 ||
        color_format > 3u || depth_format != 0 ||
        (registers.color_info & ~0x000F0FFFu) != 0 ||
        (registers.depth_info & ~0x00010FFFu) != 0 ||
        (registers.color_mask & ~0xFFFFu) != 0 || registers.window_offset != 0 ||
        (registers.blend_control_0 != 0x07010706u &&
         registers.blend_control_0 != 0x07060706u &&
         registers.blend_control_0 != 0x00010001u)) {
        return fail("unsupported captured target or raster state", error);
    }

    const bool cull_front = (registers.setup_mode_control & 1u) != 0;
    const bool cull_back = (registers.setup_mode_control & 2u) != 0;
    if (cull_front && cull_back) {
        return fail("unsupported captured front-and-back culling", error);
    }

    const float x_scale = register_float(registers.viewport_x_scale);
    const float x_offset = register_float(registers.viewport_x_offset);
    const float y_scale = register_float(registers.viewport_y_scale);
    const float y_offset = register_float(registers.viewport_y_offset);
    uint32_t viewport_width = 0;
    uint32_t viewport_height = 0;
    if (!std::isfinite(x_offset) || !std::isfinite(y_offset) ||
        !viewport_dimension(x_scale, &viewport_width) ||
        !viewport_dimension(-y_scale, &viewport_height)) {
        return fail("unsupported captured viewport or surface pitch", error);
    }
    const bool target_extent_provided = target_width != 0 || target_height != 0;
    if (target_extent_provided && (!target_width || !target_height)) {
        return fail("incomplete captured render-target extent", error);
    }
    if (!target_extent_provided &&
        (x_offset != x_scale || y_offset != -y_scale)) {
        return fail("partial captured viewport requires a known target extent", error);
    }
    if (target_extent_provided &&
        ((msaa_samples == 0 && target_width != surface_pitch) ||
         (msaa_samples == 2 &&
          (surface_pitch > std::numeric_limits<uint32_t>::max() / 2u ||
           target_width != surface_pitch * 2u)))) {
        return fail("unsupported captured viewport or surface pitch", error);
    }
    const uint32_t width = target_extent_provided ? target_width : viewport_width;
    const uint32_t height = target_extent_provided ? target_height : viewport_height;
    const float viewport_x = x_offset - x_scale;
    const float viewport_y = y_offset - y_scale;
    const float viewport_width_pixels = x_scale * 2.0f;
    const float viewport_height_pixels = y_scale * 2.0f;
    if (!std::isfinite(viewport_x) || !std::isfinite(viewport_y) ||
        !std::isfinite(viewport_width_pixels) ||
        !std::isfinite(viewport_height_pixels)) {
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
        surface_pitch,
        msaa_samples == 0 ? 1u : msaa_samples == 1 ? 2u : 4u,
        registers.color_info & 0xFFFu,
        color_format == 0 ? CapturedColorTargetFormat::Rgba8Linear
        : color_format == 1 ? CapturedColorTargetFormat::Rgba8Gamma
        : color_format == 2 ? CapturedColorTargetFormat::Rgb10A2Unorm
                            : CapturedColorTargetFormat::Rgb10A2Float,
        depth_only,
        registers.depth_info & 0xFFFu,
        CapturedDepthTargetFormat::D24S8,
        depth_only ? 0u : registers.color_mask & 0xFu,
        y_scale < 0.0f,
        ((registers.depth_control >> 1) & 1u) != 0,
        ((registers.depth_control >> 2) & 1u) != 0,
        (registers.depth_control & 1u) != 0,
        x0,
        y0,
        x1,
        y1,
        x1 > x0 && y1 > y0,
        registers.blend_control_0,
        registers.depth_control,
        registers.stencil_refmask,
        cull_front ? CapturedRasterState::CullMode::Front
                   : cull_back ? CapturedRasterState::CullMode::Back
                               : CapturedRasterState::CullMode::None,
        (registers.setup_mode_control & 4u) == 0,
        registers.setup_mode_control,
    };
    output->viewport_x = viewport_x;
    output->viewport_y = viewport_y;
    output->viewport_width = viewport_width_pixels;
    output->viewport_height = viewport_height_pixels;
    output->clip_control_valid =
        (registers.viewport_transform_valid_mask & 1u) != 0;
    output->viewport_transform_control_valid =
        (registers.viewport_transform_valid_mask & 2u) != 0;
    output->clip_disabled = output->clip_control_valid &&
        ((registers.clip_control >> 16) & 1u) != 0;
    output->viewport_transform_control = registers.viewport_transform_control;
    output->clip_disabled_window_coordinates = output->clip_disabled;
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_copy_state(
    const CapturedRasterRegisters& registers,
    CapturedCopyState* output,
    std::string* error) {
    constexpr uint32_t kCopyValidMask = 0xFu;
    constexpr uint32_t kCopyControlFields = 0x00300377u;
    constexpr uint32_t kCopyDestPitchFields = 0x3FFF3FFFu;
    constexpr uint32_t kCopyDestInfoFields = 0x01FFFFFFu;
    if (!output || registers.copy_valid_mask != kCopyValidMask) {
        return fail("captured Xenos copy register set is incomplete", error);
    }

    const uint32_t source_select = registers.copy_control & 0x7u;
    const uint32_t sample_select = (registers.copy_control >> 4) & 0x7u;
    const uint32_t clear_flags = (registers.copy_control >> 8) & 0x3u;
    const uint32_t command = (registers.copy_control >> 20) & 0x3u;
    const uint32_t destination_pitch = registers.copy_dest_pitch & 0x3FFFu;
    const uint32_t destination_height = (registers.copy_dest_pitch >> 16) & 0x3FFFu;
    const uint32_t destination_format = (registers.copy_dest_info >> 7) & 0x3Fu;
    const uint32_t destination_number = (registers.copy_dest_info >> 13) & 0x7u;
    const uint32_t destination_exp_bias = (registers.copy_dest_info >> 16) & 0x3Fu;
    if ((registers.copy_control & ~kCopyControlFields) != 0 ||
        source_select != 0 || sample_select != 0 || clear_flags != 0 ||
        command != static_cast<uint32_t>(CapturedCopyCommand::Convert) ||
        registers.copy_dest_base == 0 || (registers.copy_dest_base & 0xFFFu) != 0 ||
        (registers.copy_dest_pitch & ~kCopyDestPitchFields) != 0 ||
        destination_pitch != 1280 || destination_height != 720 ||
        (destination_pitch & 7u) != 0 || (destination_height & 7u) != 0 ||
        (registers.copy_dest_info & ~kCopyDestInfoFields) != 0 ||
        (registers.copy_dest_info & 0x7Fu) != 0 ||
        ((registers.copy_dest_info >> 4) & 0x7u) != 0 ||
        destination_format != 6 || destination_number != 0 ||
        destination_exp_bias != 0 ||
        ((registers.copy_dest_info >> 22) & 0x3u) != 0 ||
        ((registers.copy_dest_info >> 25) & 0x7Fu) != 0) {
        return fail("unsupported captured Xenos color Copy/Convert state", error);
    }

    *output = CapturedCopyState{
        source_select,
        sample_select,
        CapturedCopyCommand::Convert,
        registers.copy_dest_base,
        destination_pitch,
        destination_height,
        destination_format,
        ((registers.copy_dest_info >> 24) & 1u) != 0,
    };
    if (error) error->clear();
    return true;
}

bool captured_draw_has_no_framebuffer_effects(
    const CapturedRasterState& raster) noexcept {
    return !raster.scissor_has_area ||
           (raster.color_write_mask == 0 && !raster.depth_test_enabled &&
            !raster.depth_write_enabled && !raster.stencil_test_enabled);
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
    for (uint32_t i = 0; i < decoded.vertex_float_constants.size(); ++i) {
        decoded.vertex_float_constants[i] = read_float4(vertex_base, i);
        decoded.pixel_float_constants[i] = read_float4(pixel_base, i);
    }
    decoded.pixel_b128 = (bool_bank_words[128 / 32] & (1u << (128 % 32))) != 0;
    decoded.pixel_b129 = (bool_bank_words[129 / 32] & (1u << (129 % 32))) != 0;
    decoded.pixel_boolean_constants_valid = true;
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
    const bool r8 = texture.format == 2 && texture.endian_mode == 0;
    const bool rgba8 = texture.format == 6 && texture.endian_mode == 2;
    const bool dxt2_3 = texture.format == 19 && texture.endian_mode == 1;
    const bool dxt4_5 = texture.format == 20 && texture.endian_mode == 1;
    const bool dxt = dxt2_3 || dxt4_5;
    const bool dxt5a = texture.format == 59 && texture.endian_mode == 1;
    const bool compressed = dxt || dxt5a;
    const uint32_t bytes_per_block = dxt5a ? 8u : 16u;
    const bool valid_texture_layout = r8
        ? !texture.tiled && texture.pitch >= texture.width
        : rgba8 ? texture.tiled && texture.pitch >= texture.width &&
                      texture.pitch % 32u == 0
                : compressed && texture.width % 4u == 0 &&
                      texture.height % 4u == 0 &&
                      texture.pitch >= texture.width && texture.pitch % 4u == 0 &&
                      (!texture.tiled || texture.pitch % 128u == 0);
    if (!guest_bytes || !vulkan_bytes || (!r8 && !rgba8 && !compressed) ||
        texture.dimension != 1 || !texture.width || !texture.height ||
        !valid_texture_layout) {
        return fail("unsupported captured texture layout", error);
    }

    const uint32_t blocks_wide = (texture.width + 3u) / 4u;
    const uint32_t blocks_high = (texture.height + 3u) / 4u;
    const uint64_t output_bytes = static_cast<uint64_t>(texture.width) *
                                  texture.height * 4u;
    const uint64_t linear_block_bytes =
        static_cast<uint64_t>(blocks_wide) * blocks_high * bytes_per_block;
    const uint64_t source_bytes = r8
        ? static_cast<uint64_t>(texture.pitch) * texture.height
        : rgba8 ? tiled_rgba8_storage_bytes(texture.pitch, texture.height)
                : compressed_texture_storage_bytes(
                      texture.pitch, texture.height, bytes_per_block,
                      texture.tiled);
    if (output_bytes > std::numeric_limits<uint32_t>::max() ||
        linear_block_bytes > std::numeric_limits<uint32_t>::max() ||
        source_bytes > std::numeric_limits<uint32_t>::max() ||
        texture.byte_length != source_bytes || byte_length != source_bytes) {
        return fail("captured texture byte range does not match its dimensions", error);
    }

    if (r8) {
        std::vector<uint8_t> rgba(static_cast<size_t>(output_bytes));
        for (uint32_t y = 0; y < texture.height; ++y) {
            for (uint32_t x = 0; x < texture.width; ++x) {
                const uint8_t component =
                    guest_bytes[static_cast<size_t>(y) * texture.pitch + x];
                const size_t destination =
                    (static_cast<size_t>(y) * texture.width + x) * 4u;
                rgba[destination] = component;
                rgba[destination + 1u] = component;
                rgba[destination + 2u] = component;
                rgba[destination + 3u] = component;
            }
        }
        *vulkan_bytes = std::move(rgba);
        if (error) error->clear();
        return true;
    }

    if (compressed) {
        const uint32_t pitch_blocks = texture.pitch / 4u;
        std::vector<uint8_t> linear_blocks(static_cast<size_t>(linear_block_bytes));
        for (uint32_t y = 0; y < blocks_high; ++y) {
            for (uint32_t x = 0; x < blocks_wide; ++x) {
                const size_t source = texture.tiled
                    ? static_cast<size_t>(dxt5a
                          ? tiled_2d_offset_8bpb(x, y, pitch_blocks)
                          : tiled_2d_offset_16bpb(x, y, pitch_blocks))
                    : (static_cast<size_t>(y) * pitch_blocks + x) * bytes_per_block;
                const size_t destination =
                    (static_cast<size_t>(y) * blocks_wide + x) * bytes_per_block;
                if (source + bytes_per_block > source_bytes) {
                    return fail("captured DXT address exceeds its byte range", error);
                }
                std::copy_n(guest_bytes + source, bytes_per_block,
                            linear_blocks.begin() + destination);
            }
        }

        for (size_t offset = 0; offset < linear_blocks.size(); offset += 2u) {
            std::swap(linear_blocks[offset], linear_blocks[offset + 1u]);
        }

        if (dxt5a) {
            std::vector<uint8_t> rgba(static_cast<size_t>(output_bytes));
            for (uint32_t block_y = 0; block_y < blocks_high; ++block_y) {
                for (uint32_t block_x = 0; block_x < blocks_wide; ++block_x) {
                    const size_t block_offset =
                        (static_cast<size_t>(block_y) * blocks_wide + block_x) * 8u;
                    const Dxt5AlphaBlock alpha =
                        decode_dxt5_alpha_block(linear_blocks.data() + block_offset);
                    for (uint32_t y = 0; y < 4u; ++y) {
                        for (uint32_t x = 0; x < 4u; ++x) {
                            const uint32_t pixel = y * 4u + x;
                            const uint32_t alpha_index = static_cast<uint32_t>(
                                (alpha.indices >> (pixel * 3u)) & 7u);
                            const size_t destination =
                                (static_cast<size_t>(block_y * 4u + y) * texture.width +
                                 block_x * 4u + x) * 4u;
                            rgba[destination] = 255u;
                            rgba[destination + 1u] = 255u;
                            rgba[destination + 2u] = 255u;
                            rgba[destination + 3u] = alpha.values[alpha_index];
                        }
                    }
                }
            }
            *vulkan_bytes = std::move(rgba);
            if (error) error->clear();
            return true;
        }

        std::vector<uint8_t> rgba(static_cast<size_t>(output_bytes));
        const auto expand_565 = [](uint16_t packed, uint8_t* color) {
            color[0] = static_cast<uint8_t>(((packed >> 11) & 0x1Fu) * 255u / 31u);
            color[1] = static_cast<uint8_t>(((packed >> 5) & 0x3Fu) * 255u / 63u);
            color[2] = static_cast<uint8_t>((packed & 0x1Fu) * 255u / 31u);
        };
        for (uint32_t block_y = 0; block_y < blocks_high; ++block_y) {
            for (uint32_t block_x = 0; block_x < blocks_wide; ++block_x) {
                const size_t block_offset =
                    (static_cast<size_t>(block_y) * blocks_wide + block_x) * 16u;
                const uint8_t* block = linear_blocks.data() + block_offset;
                const auto read_le16 = [block](size_t byte) {
                    return static_cast<uint16_t>(block[byte]) |
                           (static_cast<uint16_t>(block[byte + 1u]) << 8);
                };
                const Dxt5AlphaBlock alpha = dxt4_5
                    ? decode_dxt5_alpha_block(block)
                    : Dxt5AlphaBlock{};
                const uint16_t color_0 = read_le16(8u);
                const uint16_t color_1 = read_le16(10u);
                std::array<std::array<uint8_t, 3>, 4> colors{};
                expand_565(color_0, colors[0].data());
                expand_565(color_1, colors[1].data());
                for (size_t channel = 0; channel < 3; ++channel) {
                    colors[2][channel] = static_cast<uint8_t>(
                        (2u * colors[0][channel] + colors[1][channel]) / 3u);
                    colors[3][channel] = static_cast<uint8_t>(
                        (colors[0][channel] + 2u * colors[1][channel]) / 3u);
                }
                const uint32_t indices = static_cast<uint32_t>(block[12]) |
                    (static_cast<uint32_t>(block[13]) << 8) |
                    (static_cast<uint32_t>(block[14]) << 16) |
                    (static_cast<uint32_t>(block[15]) << 24);
                for (uint32_t y = 0; y < 4u; ++y) {
                    for (uint32_t x = 0; x < 4u; ++x) {
                        const uint32_t pixel = y * 4u + x;
                        const uint32_t alpha_value = dxt4_5
                            ? alpha.values[(alpha.indices >> (pixel * 3u)) & 7u]
                            : (((block[pixel >> 1] >> ((pixel & 1u) * 4u)) & 0xFu) * 17u);
                        const uint32_t color_index = (indices >> (pixel * 2u)) & 3u;
                        const size_t destination =
                            (static_cast<size_t>(block_y * 4u + y) * texture.width +
                             block_x * 4u + x) * 4u;
                        rgba[destination] = colors[color_index][0];
                        rgba[destination + 1u] = colors[color_index][1];
                        rgba[destination + 2u] = colors[color_index][2];
                        rgba[destination + 3u] = static_cast<uint8_t>(alpha_value);
                    }
                }
            }
        }
        *vulkan_bytes = std::move(rgba);
        if (error) error->clear();
        return true;
    }

    std::vector<uint8_t> linear(static_cast<size_t>(output_bytes));
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

bool copy_captured_r8_texture_2d(
    const CapturedTextureFetch& texture,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error) {
    if (!guest_bytes || !vulkan_bytes || texture.format != 2 ||
        texture.endian_mode != 0 || texture.tiled || texture.dimension != 1 ||
        !texture.width || !texture.height || texture.pitch < texture.width) {
        return fail("unsupported captured R8 texture layout", error);
    }
    const uint64_t source_bytes = static_cast<uint64_t>(texture.pitch) * texture.height;
    const uint64_t output_bytes = static_cast<uint64_t>(texture.width) * texture.height;
    if (source_bytes > std::numeric_limits<uint32_t>::max() ||
        output_bytes > std::numeric_limits<uint32_t>::max() ||
        texture.byte_length != source_bytes || byte_length != source_bytes) {
        return fail("captured R8 texture byte range does not match its dimensions", error);
    }

    vulkan_bytes->resize(static_cast<size_t>(output_bytes));
    if (texture.pitch == texture.width) {
        std::memcpy(vulkan_bytes->data(), guest_bytes,
                    static_cast<size_t>(output_bytes));
    } else {
        for (uint32_t y = 0; y < texture.height; ++y) {
            const uint8_t* row = guest_bytes + static_cast<size_t>(y) * texture.pitch;
            std::memcpy(vulkan_bytes->data() + static_cast<size_t>(y) * texture.width,
                        row, texture.width);
        }
    }
    if (error) error->clear();
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

bool decode_captured_index_data(
    const DecodedIndexedDraw& draw,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    uint32_t* maximum_vertex_index,
    std::string* error) {
    constexpr uint32_t kMaximumCapturedIndexCount = 1u << 20;
    if (!guest_bytes || !vulkan_bytes || !maximum_vertex_index ||
        draw.index_type_bits != 16 || draw.index_endian_mode != 1 ||
        draw.index_count == 0 || draw.index_count > kMaximumCapturedIndexCount ||
        draw.index_byte_length != draw.index_count * 2u ||
        byte_length != draw.index_byte_length) {
        return fail("invalid captured 16-bit index span", error);
    }

    std::vector<uint8_t> normalized;
    if (!normalize_captured_buffer_bytes(draw.index_endian_mode, guest_bytes,
                                         byte_length, &normalized, error)) {
        return false;
    }
    uint32_t maximum = 0;
    for (uint32_t i = 0; i < draw.index_count; ++i) {
        const size_t offset = static_cast<size_t>(i) * 2;
        const uint32_t index = static_cast<uint32_t>(normalized[offset]) |
                               (static_cast<uint32_t>(normalized[offset + 1]) << 8);
        maximum = std::max(maximum, index);
    }
    *vulkan_bytes = std::move(normalized);
    *maximum_vertex_index = maximum;
    if (error) error->clear();
    return true;
}

bool captured_vertex_required_bytes(
    uint32_t maximum_vertex_index,
    uint32_t stride_bytes,
    uint32_t attribute_offset_bytes,
    uint32_t attribute_size_bytes,
    uint32_t* required_bytes,
    std::string* error) {
    if (!required_bytes || stride_bytes == 0 || attribute_size_bytes == 0 ||
        attribute_offset_bytes >= stride_bytes ||
        static_cast<uint64_t>(attribute_offset_bytes) + attribute_size_bytes >
            stride_bytes) {
        return fail("invalid captured vertex attribute span", error);
    }
    const uint64_t length = static_cast<uint64_t>(maximum_vertex_index) * stride_bytes +
                            attribute_offset_bytes + attribute_size_bytes;
    if (length > std::numeric_limits<uint32_t>::max()) {
        return fail("captured vertex span exceeds the supported address range", error);
    }
    *required_bytes = static_cast<uint32_t>(length);
    if (error) error->clear();
    return true;
}

}  // namespace shift::xbox
