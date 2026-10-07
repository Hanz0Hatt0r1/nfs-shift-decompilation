#pragma once

namespace shift::runtime::physics {

inline constexpr const char* kBmwM3E36ResponseField4054Format =
    "SHIFT.BMWM3E36ResponseField4054/1";

struct BmwM3E36ResponseField4054 {
    float wheel_fl_z = 0.0f;
    float wheel_rl_z = 0.0f;
    float value = 0.0f;
};

// Reconstructs the selected BMW M3 E36 setup-fixed HDVehicle+0x4054 value.
// PC FUN_00703f10 maps VDF Wheel FL Offset to record+0x34 and Wheel RL Offset
// to record+0x4c. FUN_007047f0 copies the selected record verbatim into the
// participant CarPhysicsDetails object used through DAT_00c133b4. During
// FUN_0076df50 setup, FUN_0076b280 loads FL.z at +0x3c and RL.z at +0x54,
// computes abs(FL.z - RL.z), and stores the f32 result at HDVehicle+0x4054.
// The selected retail BMW VDF contains FL.z=-1.35f and RL.z=+1.35f.
BmwM3E36ResponseField4054 derive_bmw_m3_e36_response_field_4054();

}  // namespace shift::runtime::physics
