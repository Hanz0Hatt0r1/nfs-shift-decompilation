#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_collision_query_contract.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40WorldPositionTransformFormat =
    "SHIFT.Fun00765c40WorldPositionTransform/1";

struct Fun00765c40WorldPositionTransformResult {
    CollisionQueryVector3d body_rotated_local{};
    CollisionQueryVector3d world_position{};
};

// PC retail FUN_00765c40 executes this exact two-stage producer immediately
// before FUN_007b0710:
//   1) FUN_007aefb0: BODY0+0xd4 3x3 f32 basis * HDVehicle+0x3938 f64 vec3;
//   2) FUN_00753590: add BODY0 origin f64 vec3 at +0x00/+0x08/+0x10.
// The upstream producer of HDVehicle+0x3938 remains a separate boundary.
Fun00765c40WorldPositionTransformResult
execute_fun_00765c40_world_position_transform(
    const BodyRecordBytes& body0,
    const CollisionQueryVector3d& local_sample_position);

}  // namespace shift::runtime::physics
