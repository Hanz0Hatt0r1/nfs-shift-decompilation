#pragma once

#include "shift_bmw_body0_bind_frame_admission.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwBody0BindFrameProofPacketFormat =
    "SHIFT.NativeBMWBody0BindFrameProofPacket/1";

struct LoadedBmwBody0BindFrameProofPacket {
    std::uint32_t version = 0u;
    std::vector<std::string> source_targets{};
    ProvenBmwBody0BindFrame admitted{};
};

LoadedBmwBody0BindFrameProofPacket load_bmw_body0_bind_frame_proof_packet(
    const std::string& path);

}  // namespace shift::runtime::physics
