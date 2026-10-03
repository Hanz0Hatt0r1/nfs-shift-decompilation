#pragma once

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyPointTransformFormat =
    "SHIFT.NativeBodyPointTransform/1";
inline constexpr const char* kBodyPointTransformFunction = "FUN_007537b0";
inline constexpr const char* kBodyPointTransformRelativeFunction = "FUN_00753810";

using BodyPointVector3d = std::array<double, 3>;

struct BodyPointTransformState {
    BodyPointVector3d angular{};
    BodyPointVector3d body_position{};
    BodyPointVector3d translation{};
};

BodyPointVector3d transform_fun_007537b0_body_point(
    const BodyPointTransformState& body,
    const BodyPointVector3d& point);

BodyPointVector3d transform_fun_00753810_body_point_relative(
    const BodyPointTransformState& body,
    const BodyPointVector3d& point);

}  // namespace shift::runtime::physics
