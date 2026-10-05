#include "shift_bmw_body0_bind_frame_proof_packet.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using shift::runtime::physics::kNativeBmwBody0BindFrameProofPacketFormat;
using shift::runtime::physics::load_bmw_body0_bind_frame_proof_packet;

#pragma pack(push, 1)
struct PacketHeader {
    char magic[4];
    std::uint32_t version;
    std::uint32_t body_index;
    std::uint32_t source_target_count;
    std::uint32_t source_target_blob_bytes;
    float matrix[16];
};
#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 84u);

void append_u32(std::vector<std::uint8_t>& bytes, std::uint32_t value) {
    const auto* raw = reinterpret_cast<const std::uint8_t*>(&value);
    bytes.insert(bytes.end(), raw, raw + sizeof(value));
}

std::vector<std::uint8_t> packet_bytes() {
    const std::array<const char*, 4> targets{{
        "FUN_007b3670",
        "FUN_007bba90",
        "FUN_007bbb10",
        "FUN_007bbb60",
    }};
    std::vector<std::uint8_t> blob;
    for (const char* target : targets) {
        const std::size_t length = std::strlen(target);
        append_u32(blob, static_cast<std::uint32_t>(length));
        const auto* begin = reinterpret_cast<const std::uint8_t*>(target);
        blob.insert(blob.end(), begin, begin + length);
    }

    PacketHeader header{};
    std::memcpy(header.magic, "BBFP", 4u);
    header.version = 1u;
    header.body_index = 0u;
    header.source_target_count = static_cast<std::uint32_t>(targets.size());
    header.source_target_blob_bytes = static_cast<std::uint32_t>(blob.size());
    const float matrix[16] = {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        1.25f, -0.5f, 2.0f, 1.0f,
    };
    std::copy(std::begin(matrix), std::end(matrix), std::begin(header.matrix));

    std::vector<std::uint8_t> bytes(sizeof(header));
    std::memcpy(bytes.data(), &header, sizeof(header));
    bytes.insert(bytes.end(), blob.begin(), blob.end());
    return bytes;
}

std::filesystem::path write_packet(
    const std::string& name,
    const std::vector<std::uint8_t>& bytes) {
    const auto path = std::filesystem::temp_directory_path() / name;
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
        throw std::runtime_error("cannot create packet fixture");
    }
    out.write(
        reinterpret_cast<const char*>(bytes.data()),
        static_cast<std::streamsize>(bytes.size()));
    if (!out) {
        throw std::runtime_error("cannot write packet fixture");
    }
    return path;
}

template <typename Mutator>
void require_rejected(const char* label, Mutator mutator) {
    auto bytes = packet_bytes();
    mutator(bytes);
    const auto path = write_packet(
        std::string("shift_bmw_body0_bind_packet_bad_") + label + ".bin",
        bytes);
    try {
        (void)load_bmw_body0_bind_frame_proof_packet(path.string());
    } catch (const std::exception&) {
        std::filesystem::remove(path);
        return;
    }
    std::filesystem::remove(path);
    throw std::runtime_error(std::string("packet loader accepted ") + label);
}

PacketHeader header_from(const std::vector<std::uint8_t>& bytes) {
    PacketHeader header{};
    std::memcpy(&header, bytes.data(), sizeof(header));
    return header;
}

void write_header(std::vector<std::uint8_t>& bytes, const PacketHeader& header) {
    std::memcpy(bytes.data(), &header, sizeof(header));
}

}  // namespace

int main() {
    const auto positive_path = write_packet(
        "shift_bmw_body0_bind_packet_positive.bin",
        packet_bytes());
    const auto loaded = load_bmw_body0_bind_frame_proof_packet(
        positive_path.string());
    std::filesystem::remove(positive_path);

    if (loaded.version != 1u || loaded.source_targets.size() != 4u) {
        throw std::runtime_error("positive packet lost version or source targets");
    }
    if (!loaded.admitted.ready || !loaded.admitted.evidence_proven_static ||
        loaded.admitted.body_index != 0u || loaded.admitted.identity_matrix_assumed) {
        throw std::runtime_error("positive packet did not pass strict native admission");
    }
    if (loaded.admitted.body0_local_to_vhf_vehicle_root[12] != 1.25f ||
        loaded.admitted.body0_local_to_vhf_vehicle_root[13] != -0.5f ||
        loaded.admitted.body0_local_to_vhf_vehicle_root[14] != 2.0f) {
        throw std::runtime_error("positive packet changed the source-backed matrix");
    }

    require_rejected("magic", [](auto& bytes) {
        bytes[0] = static_cast<std::uint8_t>('X');
    });
    require_rejected("version", [](auto& bytes) {
        auto header = header_from(bytes);
        header.version = 2u;
        write_header(bytes, header);
    });
    require_rejected("body_index", [](auto& bytes) {
        auto header = header_from(bytes);
        header.body_index = 1u;
        write_header(bytes, header);
    });
    require_rejected("zero_targets", [](auto& bytes) {
        auto header = header_from(bytes);
        header.source_target_count = 0u;
        write_header(bytes, header);
    });
    require_rejected("blob_size", [](auto& bytes) {
        auto header = header_from(bytes);
        ++header.source_target_blob_bytes;
        write_header(bytes, header);
    });
    require_rejected("singular_matrix", [](auto& bytes) {
        auto header = header_from(bytes);
        header.matrix[0] = 0.0f;
        write_header(bytes, header);
    });
    require_rejected("truncated", [](auto& bytes) {
        bytes.resize(sizeof(PacketHeader));
    });

    std::cout
        << "{\"format\":\"" << kNativeBmwBody0BindFrameProofPacketFormat << "\","
        << "\"magic\":\"BBFP\","
        << "\"version\":1,"
        << "\"native_loader_ready\":true,"
        << "\"strict_admission_reused\":true,"
        << "\"source_targets_preserved\":true,"
        << "\"current_retail_proof_present\":false,"
        << "\"retail_world_transform_admitted\":false}"
        << '\n';
    return 0;
}
