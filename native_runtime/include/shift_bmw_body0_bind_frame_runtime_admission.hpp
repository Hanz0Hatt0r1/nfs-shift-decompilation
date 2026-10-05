#pragma once

#include "shift_bmw_body0_bind_frame_proof_packet.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {

inline constexpr const char* kBmwBody0BindFrameProofPacketEnv =
    "SHIFT_NATIVE_BMW_BODY0_BIND_PROOF_PACKET";
inline constexpr const char* kNativeBmwBody0BindFrameRuntimeAdmissionFormat =
    "SHIFT.NativeBMWBody0BindFrameRuntimeAdmission/1";

struct BmwBody0BindFrameRuntimeAdmissionState {
    bool configured = false;
    bool admitted = false;
    std::string packet_path{};
    std::size_t source_target_count = 0u;
    ProvenBmwBody0BindFrame bind_frame{};
};

namespace body0_bind_runtime_admission_detail {

inline BmwBody0BindFrameRuntimeAdmissionState& state() {
    static BmwBody0BindFrameRuntimeAdmissionState value{};
    return value;
}

}  // namespace body0_bind_runtime_admission_detail

// Production-facing P2.1 gate. The runtime may discover a positive Process 1
// proof only through the BBFP packet produced by the strict positive-only
// builder. Absence is intentionally inert while Process 1 still owns the
// semantic blocker. A supplied packet is fail-closed before the physics tick.
inline const BmwBody0BindFrameRuntimeAdmissionState&
admit_bmw_body0_bind_frame_from_environment_once() {
    auto& state = body0_bind_runtime_admission_detail::state();
    const char* raw_path = std::getenv(kBmwBody0BindFrameProofPacketEnv);
    if (raw_path == nullptr || *raw_path == '\0') {
        if (state.configured) {
            throw std::logic_error(
                "BODY0 bind proof packet environment disappeared after admission");
        }
        return state;
    }

    const std::string path(raw_path);
    if (state.configured) {
        if (state.packet_path != path) {
            throw std::logic_error(
                "BODY0 bind proof packet path changed after runtime admission");
        }
        return state;
    }

    const auto loaded = load_bmw_body0_bind_frame_proof_packet(path);
    if (!loaded.admitted.ready || !loaded.admitted.evidence_proven_static) {
        throw std::logic_error(
            "BODY0 bind proof packet loader returned a non-positive admission");
    }

    state.configured = true;
    state.admitted = true;
    state.packet_path = path;
    state.source_target_count = loaded.source_targets.size();
    state.bind_frame = loaded.admitted;

    std::cout
        << "{\"format\":\""
        << kNativeBmwBody0BindFrameRuntimeAdmissionFormat
        << "\",\"ready\":true"
        << ",\"upstream_packet_format\":\""
        << kNativeBmwBody0BindFrameProofPacketFormat << "\""
        << ",\"body_index\":" << state.bind_frame.body_index
        << ",\"source_target_count\":" << state.source_target_count
        << ",\"retail_bind_frame_admitted\":true"
        << ",\"retail_scheduler_claimed\":false"
        << ",\"vehicle_world_transform_committed\":false}\n";
    return state;
}

inline const BmwBody0BindFrameRuntimeAdmissionState&
current_bmw_body0_bind_frame_runtime_admission() {
    return body0_bind_runtime_admission_detail::state();
}

}  // namespace shift::runtime::physics
