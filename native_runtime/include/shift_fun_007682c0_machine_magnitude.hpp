#pragma once

namespace shift::runtime::physics {

inline constexpr const char* kFun007682c0MachineMagnitudeFormat =
    "SHIFT.Fun007682c0MachineMagnitude/1";

struct Fun007682c0MachineMagnitudeResult {
    float speed_3d = 0.0f;
    bool speed_gate_open = false;
    float speed_factor = 0.0f;
};

// PC retail FUN_007682c0 at 0x007682dc..0x00768305:
// load BODY +0x78/+0x80/+0x88 as f64, evaluate x^2+y^2+z^2 in x87,
// call __CIsqrt (FSQRT under retail CW 0x027f), then FSTP f32.
float fun_007682c0_pc_x87_speed3d_f32(
    double motion_x,
    double motion_y,
    double motion_z);

// PC retail FUN_0075ada0 at 0x0075adaf..0x0075ade2:
// narrow BODY +0x78/+0x88 f64 lanes to f32, evaluate the planar squared
// magnitude in x87, FSTP the radicand to f32, reload, FSQRT, FSTP f32.
float fun_0075ada0_pc_x87_planar_speed_f32(
    double motion_x,
    double motion_z);

// Source/machine FUN_007682c0 gate and f32 speed-factor checkpoint after
// (speed - 5) / 15 and [0,1] clamp.
Fun007682c0MachineMagnitudeResult
fun_007682c0_pc_machine_magnitude(
    double motion_x,
    double motion_y,
    double motion_z);

}  // namespace shift::runtime::physics
