#pragma once

#include "shift_bmw_body0_vhf_world_matrix_composition.hpp"

#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kBmwBody0BindFrameProofFormat =
    "SHIFT.BMWBody0BindFrameProof/1";
inline constexpr const char* kNativeBmwBody0BindFrameAdmissionFormat =
    "SHIFT.NativeBMWBody0BindFrameAdmission/1";

struct BmwBody0BindFrameProofHandoff {
    const char* format = nullptr;
    bool ready = false;
    const char* status = nullptr;
    const char* evidence_state = nullptr;
    std::uint32_t body_index = 0u;
    const char* body_name = nullptr;
    const char* frame_relation = nullptr;
    const char* matrix_convention = nullptr;
    const char* const* source_targets = nullptr;
    std::size_t source_target_count = 0u;
    bool identity_matrix_assumed = true;
    bool original_game_executed = true;
    bool new_runtime_capture_used = true;
    shift::runtime::render::VehicleWorldMatrix
        body0_local_to_vhf_vehicle_root_row_matrix{};
};

ProvenBmwBody0BindFrame admit_bmw_body0_bind_frame_proof(
    const BmwBody0BindFrameProofHandoff& proof);

}  // namespace shift::runtime::physics
