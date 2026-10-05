#include "shift_bmw_body0_bind_frame_proof_packet.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::physics {
namespace {

constexpr std::array<char, 4> kMagic{{'B', 'B', 'F', 'P'}};
constexpr std::uint32_t kVersion = 1u;
constexpr std::uint32_t kRetailBmwChassisBodyIndex = 0u;
constexpr std::uint32_t kMaxSourceTargets = 128u;
constexpr std::uint32_t kMaxSourceTargetBytes = 4096u;
constexpr std::size_t kMaxPacketBytes = 1024u * 1024u;

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

std::vector<std::uint8_t> read_packet(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open BMW BODY0 bind-frame proof packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size < static_cast<std::streamsize>(sizeof(PacketHeader))) {
        throw std::runtime_error("BMW BODY0 bind-frame proof packet is truncated");
    }
    if (size > static_cast<std::streamsize>(kMaxPacketBytes)) {
        throw std::runtime_error("BMW BODY0 bind-frame proof packet is too large");
    }
    stream.seekg(0);
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));
    if (!stream.read(reinterpret_cast<char*>(bytes.data()), size)) {
        throw std::runtime_error("cannot read BMW BODY0 bind-frame proof packet");
    }
    return bytes;
}

std::uint32_t read_u32(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset > bytes.size() || bytes.size() - offset < sizeof(std::uint32_t)) {
        throw std::runtime_error(
            "BMW BODY0 bind-frame proof packet target table is truncated");
    }
    std::uint32_t value = 0u;
    std::memcpy(&value, bytes.data() + offset, sizeof(value));
    return value;
}

std::vector<std::string> decode_source_targets(
    const std::vector<std::uint8_t>& bytes,
    const PacketHeader& header) {
    if (header.source_target_count == 0u ||
        header.source_target_count > kMaxSourceTargets) {
        throw std::invalid_argument(
            "BMW BODY0 bind-frame proof packet source target count is invalid");
    }

    const std::size_t blob_offset = sizeof(PacketHeader);
    const std::size_t blob_bytes =
        static_cast<std::size_t>(header.source_target_blob_bytes);
    if (blob_bytes != bytes.size() - blob_offset) {
        throw std::invalid_argument(
            "BMW BODY0 bind-frame proof packet source target blob size mismatch");
    }

    std::size_t cursor = blob_offset;
    std::vector<std::string> targets;
    targets.reserve(header.source_target_count);
    for (std::uint32_t index = 0u; index < header.source_target_count; ++index) {
        const std::uint32_t length = read_u32(bytes, cursor);
        cursor += sizeof(std::uint32_t);
        if (length == 0u || length > kMaxSourceTargetBytes) {
            throw std::invalid_argument(
                "BMW BODY0 bind-frame proof packet source target length is invalid");
        }
        if (cursor > bytes.size() || bytes.size() - cursor < length) {
            throw std::invalid_argument(
                "BMW BODY0 bind-frame proof packet source target is truncated");
        }
        const char* begin = reinterpret_cast<const char*>(bytes.data() + cursor);
        if (std::memchr(begin, '\0', length) != nullptr) {
            throw std::invalid_argument(
                "BMW BODY0 bind-frame proof packet source target contains NUL");
        }
        targets.emplace_back(begin, begin + length);
        cursor += length;
    }
    if (cursor != bytes.size()) {
        throw std::invalid_argument(
            "BMW BODY0 bind-frame proof packet contains trailing target bytes");
    }
    return targets;
}

}  // namespace

LoadedBmwBody0BindFrameProofPacket load_bmw_body0_bind_frame_proof_packet(
    const std::string& path) {
    const auto bytes = read_packet(path);

    PacketHeader header{};
    std::memcpy(&header, bytes.data(), sizeof(header));
    if (!std::equal(kMagic.begin(), kMagic.end(), header.magic)) {
        throw std::invalid_argument(
            "BMW BODY0 bind-frame proof packet has wrong magic");
    }
    if (header.version != kVersion) {
        throw std::invalid_argument(
            "BMW BODY0 bind-frame proof packet version is unsupported");
    }
    if (header.body_index != kRetailBmwChassisBodyIndex) {
        throw std::invalid_argument(
            "BMW BODY0 bind-frame proof packet does not identify chassis BODY 0");
    }

    auto targets = decode_source_targets(bytes, header);
    std::vector<const char*> target_pointers;
    target_pointers.reserve(targets.size());
    for (const auto& target : targets) {
        target_pointers.push_back(target.c_str());
    }

    shift::runtime::render::VehicleWorldMatrix matrix{};
    std::copy(std::begin(header.matrix), std::end(header.matrix), matrix.begin());

    BmwBody0BindFrameProofHandoff proof{};
    proof.format = kBmwBody0BindFrameProofFormat;
    proof.ready = true;
    proof.status = "ready";
    proof.evidence_state = "proven-static";
    proof.body_index = header.body_index;
    proof.body_name = "body";
    proof.frame_relation = "BODY0-local-to-VHF-vehicle-root";
    proof.matrix_convention = "row-major D3D row-vector affine";
    proof.source_targets = target_pointers.data();
    proof.source_target_count = target_pointers.size();
    proof.identity_matrix_assumed = false;
    proof.original_game_executed = false;
    proof.new_runtime_capture_used = false;
    proof.body0_local_to_vhf_vehicle_root_row_matrix = matrix;

    LoadedBmwBody0BindFrameProofPacket result{};
    result.version = header.version;
    result.source_targets = std::move(targets);
    result.admitted = admit_bmw_body0_bind_frame_proof(proof);
    return result;
}

}  // namespace shift::runtime::physics
