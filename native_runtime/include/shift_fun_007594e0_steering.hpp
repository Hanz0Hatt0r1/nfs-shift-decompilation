#pragma once

#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007594e0SteeringFormat =
    "SHIFT.NativeFun007594e0Steering/1";

struct Fun007594e0SteeringResult {
    float steering = 0.0f;
    double local_velocity_x = 0.0;
    double local_velocity_z = 0.0;
    double planar_squared = 0.0;
    bool angle_gate_open = false;
    bool x87_fpatan_used = false;
};

// Reconstructs the PC retail FUN_007594e0 value later stored to
// HDVehicle+0x4068 by FUN_0076f970. The source reads the chassis BODY0
// velocity at +0x78/+0x80/+0x88, transforms it by the BODY0 f32 basis at
// +0xd4..+0xf4, opens the angle path only for local_x^2 + local_z^2 > 0.1,
// then evaluates atan2(-local_x, -local_z) through the retail x87 FPATAN path
// and finally spills the caller-visible HDVehicle field to f32.
Fun007594e0SteeringResult execute_fun_007594e0_steering(
    const std::vector<std::uint8_t>& current_body_bytes);

}  // namespace shift::runtime::physics
