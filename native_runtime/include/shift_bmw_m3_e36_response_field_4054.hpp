#pragma once

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kBmwM3E36ResponseField4054Format =
    "SHIFT.BMWM3E36ResponseField4054/1";

inline constexpr std::uint32_t kBmwM3E36WheelFlZBits = 0xbfaccccdu;
inline constexpr std::uint32_t kBmwM3E36WheelRlZBits = 0x3faccccdu;
inline constexpr std::uint32_t kBmwM3E36ResponseField4054Bits = 0x402ccccdu;

// PC FUN_0076b280 widens the selected CarPhysicsDetails Wheel FL/RL Offset Z
// f32 values to x87, evaluates fabs(FL.z - RL.z), and stores the result to
// HDVehicle+0x4054 as f32 during vehicle setup. For the selected BMW M3 E36,
// the hash-locked VDF publishes FL.z=-1.35f and RL.z=+1.35f.
float selected_bmw_m3_e36_response_field_4054();

}  // namespace shift::runtime::physics
