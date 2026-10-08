#include "shift_body_accumulator_primitives.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_body(
    const BodyAccumulatorState& body,
    const char* label) {
    require_finite(body.angular, label);
    require_finite(body.linear, label);
}

void apply_signed_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& point_or_lever_arm,
    const BodyAccumulatorVector3d& contribution,
    double sign,
    const char* label) {

    require_finite_body(body, label);
    require_finite(point_or_lever_arm, label);
    require_finite(contribution, label);

    const auto angular_delta =
        execute_fun_00753650_cross_product(
            point_or_lever_arm,
            contribution);
    for (std::size_t component = 0; component < 3u; ++component) {
        body.linear[component] += sign * contribution[component];
        body.angular[component] += sign * angular_delta[component];
    }
    require_finite_body(body, label);
}

}  // namespace

BodyAccumulatorVector3d execute_fun_00753650_cross_product(
    const BodyAccumulatorVector3d& left,
    const BodyAccumulatorVector3d& right) {
    require_finite(left, "FUN_00753650 left vector");
    require_finite(right, "FUN_00753650 right vector");
    const BodyAccumulatorVector3d result = {
        right[2] * left[1] - left[2] * right[1],
        left[2] * right[0] - right[2] * left[0],
        right[1] * left[0] - right[0] * left[1],
    };
    require_finite(result, "FUN_00753650 result");
    return result;
}

void apply_fun_007baa70_body_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& point_or_lever_arm,
    const BodyAccumulatorVector3d& contribution) {

    apply_signed_accumulator(
        body,
        point_or_lever_arm,
        contribution,
        1.0,
        "FUN_007baa70 BODY accumulator");
}

void apply_fun_007baaf0_body_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& point_or_lever_arm,
    const BodyAccumulatorVector3d& contribution) {

    apply_signed_accumulator(
        body,
        point_or_lever_arm,
        contribution,
        -1.0,
        "FUN_007baaf0 BODY accumulator");
}

void apply_fun_007ba9e0_point_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& world_point,
    const BodyAccumulatorVector3d& body_origin,
    const BodyAccumulatorVector3d& contribution) {

    require_finite(world_point, "FUN_007ba9e0 world point");
    require_finite(body_origin, "FUN_007ba9e0 BODY origin");
    BodyAccumulatorVector3d relative_point = {
        world_point[0] - body_origin[0],
        world_point[1] - body_origin[1],
        world_point[2] - body_origin[2],
    };
    require_finite(relative_point, "FUN_007ba9e0 relative point");
    apply_fun_007baa70_body_accumulator(
        body,
        relative_point,
        contribution);
}

}  // namespace shift::runtime::physics
