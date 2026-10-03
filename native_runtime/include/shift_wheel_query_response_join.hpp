#pragma once

#include "shift_collision_query_contract.hpp"
#include "shift_wheel_contact_response.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelQueryResponseJoinFormat =
    "SHIFT.NativeWheelQueryResponseJoin/1";
inline constexpr const char* kWheelQueryProducerFunction = "FUN_00765c40";
inline constexpr const char* kWheelQueryResponseConsumerFunction = "FUN_00766510";
inline constexpr std::size_t kWheelQueryScalarOffset = 0x38e0u;
inline constexpr std::size_t kWheelQueryLimitOffset = 0x38e8u;
inline constexpr std::size_t kWheelResponseGainOffset = 0x39d0u;

struct WheelQueryResponseJoinInput {
    double original_world_y = 0.0;
    double fallback_and_query_limit = 0.0;
    CollisionQueryOutput query_output{};

    double depth_slope = 0.0;
    double base_offset = 0.0;
    WheelContactCurveParameters directional_curve{};
    WheelContactResponseTable response_table{};
    double tangent_x = 0.0;
    double tangent_z = 0.0;
    ConstraintRefreshFrame3f body_frame{};
    WheelContactVector3d body_source_vector{};
};

struct WheelQueryResponseJoinResult {
    double caller_query_scalar = 0.0;
    double query_limit = 0.0;
    WheelContactResponse response{};
};

WheelQueryResponseJoinResult execute_fun_00765c40_to_00766510_response_join(
    const WheelQueryResponseJoinInput& input);

}  // namespace shift::runtime::physics
