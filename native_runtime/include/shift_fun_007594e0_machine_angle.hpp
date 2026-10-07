#pragma once

#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007594e0MachineAngleFormat =
    "SHIFT.NativeFun007594e0MachineAngle/1";

struct Fun007594e0MachineAngleResult {
    float steering = 0.0f;
    double local_x = 0.0;
    double local_z = 0.0;
    double planar_squared = 0.0;
    bool planar_gate_open = false;
    bool x87_fpatan_used = false;
};

// Reconstructs the PC retail FUN_007594e0 producer used by FUN_0076f970 before
// FUN_00770e80's two physics passes. BODY0 motion (+0x78/+0x80/+0x88) is
// transformed through the BODY0 3x3 f32 basis at +0xd4..+0xf4. A steering
// angle is produced only when local_x^2 + local_z^2 is strictly greater than
// the retail f64 0.1 gate. The finite normal CRT atan2 path is reproduced with
// x87 FPATAN under control word 0x027f and spilled to f32 exactly where
// FUN_0076f970 stores HDVehicle+0x4068.
Fun007594e0MachineAngleResult execute_fun_007594e0_machine_angle(
    const std::vector<std::uint8_t>& current_body_bytes);

}  // namespace shift::runtime::physics
