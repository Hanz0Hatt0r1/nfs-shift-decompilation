#pragma once

namespace shift::runtime::physics {

inline constexpr const char* kFun007560c0MotionReadGateSetupFormat =
    "SHIFT.Fun007560c0MotionReadGateSetup/1";

// PC retail FUN_007560c0 snapshots HDVehicle+0xe0 during vehicle setup.
// FUN_00769ef0 later reads that stored byte; it does not refresh the value per
// physics pass. Keep the selected setup value explicit until its upstream
// settings producer is proven, but remove it from the late motion-read provider.
struct Fun007560c0MotionReadGateSetup {
    bool caller_gate_open = false;
};

}  // namespace shift::runtime::physics
