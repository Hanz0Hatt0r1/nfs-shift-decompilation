#include "shift_bmw_body0_bind_frame_runtime_admission.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using shift::runtime::physics::admit_bmw_body0_bind_frame_from_environment_once;
using shift::runtime::physics::current_bmw_body0_bind_frame_runtime_admission;
using shift::runtime::physics::kBmwBody0BindFrameProofPacketEnv;
using shift::runtime::physics::kNativeBmwBody0BindFrameRuntimeAdmissionFormat;

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

std::filesystem::path write_packet(const std::string& name) {
    const auto path = std::filesystem::temp_directory_path() / name;
    const auto bytes = packet_bytes();
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
        throw std::runtime_error("cannot create runtime-admission packet fixture");
    }
    out.write(
        reinterpret_cast<const char*>(bytes.data()),
        static_cast<std::streamsize>(bytes.size()));
    if (!out) {
        throw std::runtime_error("cannot write runtime-admission packet fixture");
    }
    return path;
}

void require_logic_error(const char* label) {
    try {
        (void)admit_bmw_body0_bind_frame_from_environment_once();
    } catch (const std::logic_error&) {
        return;
    }
    throw std::runtime_error(std::string("runtime admission accepted ") + label);
}

}  // namespace

int main() {
    ::unsetenv(kBmwBody0BindFrameProofPacketEnv);
    const auto& absent = admit_bmw_body0_bind_frame_from_environment_once();
    if (absent.configured || absent.admitted) {
        throw std::runtime_error("absent BODY0 bind proof packet was not inert");
    }

    const auto first_path = write_packet("shift_body0_runtime_admission_a.bbfp");
    if (::setenv(
            kBmwBody0BindFrameProofPacketEnv,
            first_path.c_str(),
            1) != 0) {
        throw std::runtime_error("cannot set BODY0 bind proof packet environment");
    }

    const auto& admitted = admit_bmw_body0_bind_frame_from_environment_once();
    if (!admitted.configured || !admitted.admitted ||
        admitted.packet_path != first_path.string() ||
        admitted.source_target_count != 4u ||
        !admitted.bind_frame.ready ||
        !admitted.bind_frame.evidence_proven_static ||
        admitted.bind_frame.body_index != 0u ||
        admitted.bind_frame.identity_matrix_assumed) {
        throw std::runtime_error("positive BODY0 bind proof packet was not retained");
    }

    const auto& repeated = admit_bmw_body0_bind_frame_from_environment_once();
    if (&repeated != &admitted || repeated.packet_path != first_path.string()) {
        throw std::runtime_error("same BODY0 bind proof packet admission was not stable");
    }

    const auto second_path = write_packet("shift_body0_runtime_admission_b.bbfp");
    if (::setenv(
            kBmwBody0BindFrameProofPacketEnv,
            second_path.c_str(),
            1) != 0) {
        throw std::runtime_error("cannot change BODY0 bind proof packet environment");
    }
    require_logic_error("changed proof packet path");

    if (::setenv(
            kBmwBody0BindFrameProofPacketEnv,
            first_path.c_str(),
            1) != 0) {
        throw std::runtime_error("cannot restore BODY0 bind proof packet environment");
    }
    ::unsetenv(kBmwBody0BindFrameProofPacketEnv);
    require_logic_error("removed proof packet after admission");

    std::filesystem::remove(first_path);
    std::filesystem::remove(second_path);

    const auto& final_state = current_bmw_body0_bind_frame_runtime_admission();
    if (!final_state.admitted || final_state.source_target_count != 4u) {
        throw std::runtime_error("runtime admission state was not preserved");
    }

    std::cout
        << "{\"format\":\""
        << kNativeBmwBody0BindFrameRuntimeAdmissionFormat
        << "\",\"ready\":true"
        << ",\"environment\":\""
        << kBmwBody0BindFrameProofPacketEnv << "\""
        << ",\"absent_packet_is_inert\":true"
        << ",\"positive_packet_admitted_before_tick\":true"
        << ",\"path_change_rejected\":true"
        << ",\"path_removal_rejected\":true"
        << ",\"retail_scheduler_claimed\":false"
        << ",\"vehicle_world_transform_committed\":false}\n";
    return 0;
}
