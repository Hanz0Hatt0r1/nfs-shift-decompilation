#pragma once

#include "shift_fun_00770e80_motion_read_effect_provider_chain.hpp"

#include <array>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007682c0MachineEffectFormat =
    "SHIFT.NativeFun007682c0MachineEffect/1";

// Raw non-BODY inputs visible at the PC retail FUN_00769ef0 -> FUN_007682c0
// boundary. BODY0-owned values are intentionally read from the persistent
// 0x170-byte BODY record by execute_fun_007682c0_machine_effect().
struct Fun007682c0MachineInput {
    // FUN_00769ef0 only calls FUN_007682c0 when HDVehicle+0xe0 is non-zero.
    bool caller_gate_open = false;

    // HDVehicle+0x4068, forwarded as FUN_007682c0 param_1.
    float steering = 0.0f;

    // QWORD fields HDVehicle+0xb38/+0x15b8/+0x2038/+0x2ab8. Their sum is
    // divided by BODY0+0x120 * 9.81 and clamped to [0,1] before being passed as
    // FUN_007682c0 param_2.
    std::array<double, 4> load_terms{};

    // FUN_0075ada0 projection inputs HDVehicle+0x4084/+0x408c.
    float projection_field_x = 0.0f;
    float projection_field_z = 0.0f;

    // FUN_007595d0 input HDVehicle+0x4054.
    float response_field_4054 = 0.0f;

    // DAT_00c128cc selects the 40-degree (<2) or 55-degree (>=2) limit.
    std::int32_t angle_mode = 0;
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
    bool x87_fsqrt_used = false;
};

// Reconstructs the PC retail FUN_00769ef0 caller-scale production plus the
// FUN_007682c0 -> FUN_0075ada0 -> FUN_007595d0 effect arithmetic. The two
// retail square-root sites use x87 FSQRT with the observed 0x027f control word
// on x86/x86_64; no host std::sqrt substitution is used.
Fun007682c0MachineEffectResult execute_fun_007682c0_machine_effect(
    const Fun007682c0MachineInput& input,
    const std::vector<std::uint8_t>& current_body_bytes);

}  // namespace shift::runtime::physics
