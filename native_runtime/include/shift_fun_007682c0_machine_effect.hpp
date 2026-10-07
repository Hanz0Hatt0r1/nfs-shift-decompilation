#pragma once

#include "shift_fun_00770e80_motion_read_effect_provider_chain.hpp"

#include <array>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007682c0MachineEffectFormat =
    "SHIFT.NativeFun007682c0MachineEffect/1";

// Raw non-BODY inputs visible at the PC retail FUN_00769ef0 -> FUN_007682c0
// boundary. BODY0-owned values are read from the current persistent 0x170-byte
// BODY record by execute_fun_007682c0_machine_effect().
struct Fun007682c0MachineInput {
    bool caller_gate_open = false; // HDVehicle+0xe0
    float steering = 0.0f;         // HDVehicle+0x4068
    std::array<double, 4> load_terms{}; // +0xb38/+0x15b8/+0x2038/+0x2ab8
    float projection_field_x = 0.0f; // HDVehicle+0x4084
    float projection_field_z = 0.0f; // HDVehicle+0x408c
    float response_field_4054 = 0.0f;
    std::int32_t angle_mode = 0; // DAT_00c128cc
};

struct Fun007682c0MachineEffectResult {
    Fun007682c0AccumulatorEffect effect{};
    float speed_3d = 0.0f;
    float speed_factor = 0.0f;
    float caller_scale = 0.0f;
    float planar_speed = 0.0f;
    float reciprocal_like = 0.0f;
    float response = 0.0f;
    bool caller_gate_open = false;
    bool speed_gate_open = false;
    bool planar_geometry_valid = false;
    bool upstream_machine_magnitude_used = false;
};

// Consumes SHIFT.Fun007682c0MachineMagnitude/1 for the proven PC x87 magnitude
// and speed-factor checkpoints, then reconstructs the remaining FUN_0075ada0
// geometry, FUN_007595d0 response and caller-scale path with explicit retail
// f32 store/reload boundaries.
Fun007682c0MachineEffectResult execute_fun_007682c0_machine_effect(
    const Fun007682c0MachineInput& input,
    const std::vector<std::uint8_t>& current_body_bytes);

}  // namespace shift::runtime::physics
