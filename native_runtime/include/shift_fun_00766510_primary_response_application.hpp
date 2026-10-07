#pragma once

#include "shift_body_accumulator_primitives.hpp"
#include "shift_constraint_sample_refresh.hpp"
#include "shift_wheel_contact_response.hpp"

#include <array>
#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510PrimaryResponseApplicationFormat =
    "SHIFT.Fun00766510PrimaryResponseApplication/1";

inline constexpr std::size_t kFun00766510PrimaryLeverArmOffset = 0x38f0u;
inline constexpr std::size_t kFun00766510PrimaryResponseTableOffset = 0x3950u;
inline constexpr std::size_t kFun00766510CallerCrossAccumulatorOffset = 0x40a0u;

struct Fun00766510PrimaryResponseApplicationInput {
    ConstraintRefreshFrame3f body_frame{};
    BodyAccumulatorState body_accumulator{};
    BodyAccumulatorVector3d point_or_lever_arm{};
    WheelContactVector3d response_vector{};
    WheelContactVector3d auxiliary_response{};
    BodyAccumulatorVector3d caller_reference_vector{};
    BodyAccumulatorVector3d caller_cross_accumulator{};
    WheelContactVector3d auxiliary_accumulator{};
};

struct Fun00766510PrimaryResponseApplicationResult {
    BodyAccumulatorVector3d transformed_response{};
    BodyAccumulatorState body_accumulator{};
    BodyAccumulatorVector3d caller_cross_delta{};
    BodyAccumulatorVector3d caller_cross_accumulator{};
    WheelContactVector3d auxiliary_accumulator{};
};

namespace detail {

template <typename Range>
inline void require_fun_00766510_finite(
    const Range& values,
    const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

inline BodyAccumulatorVector3d fun_00753650_cross(
    const BodyAccumulatorVector3d& left,
    const BodyAccumulatorVector3d& right) {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

}  // namespace detail

// PC retail FUN_00766510 primary query-response application, source lines
// 759686..759695 / machine span beginning at 0x00766f9f:
//   1. FUN_007551e0 has already produced response_vector + auxiliary_response.
//   2. FUN_007aefb0 transforms response_vector by BODY+0xd4.
//   3. FUN_007baa70 applies that transformed vector at HDVehicle+0x38f0.
//   4. FUN_00753650(caller_reference_vector, transformed_response) is added to
//      HDVehicle+0x40a0/+0x40a8/+0x40b0.
//   5. the three auxiliary lanes accumulate into the caller-local vector later
//      finalized by FUN_00766510.
//
// This helper intentionally does not invent producers for point_or_lever_arm,
// caller_reference_vector or either incoming accumulator. Those remain explicit
// caller-state inputs until separate ownership proofs close them.
inline Fun00766510PrimaryResponseApplicationResult
execute_fun_00766510_primary_response_application(
    const Fun00766510PrimaryResponseApplicationInput& input) {
    detail::require_fun_00766510_finite(input.body_frame, "FUN_00766510 BODY frame");
    detail::require_fun_00766510_finite(
        input.body_accumulator.angular,
        "FUN_00766510 BODY angular accumulator");
    detail::require_fun_00766510_finite(
        input.body_accumulator.linear,
        "FUN_00766510 BODY linear accumulator");
    detail::require_fun_00766510_finite(
        input.point_or_lever_arm,
        "FUN_00766510 +0x38f0 point/lever arm");
    detail::require_fun_00766510_finite(
        input.response_vector,
        "FUN_00766510 FUN_007551e0 response vector");
    detail::require_fun_00766510_finite(
        input.auxiliary_response,
        "FUN_00766510 FUN_007551e0 auxiliary response");
    detail::require_fun_00766510_finite(
        input.caller_reference_vector,
        "FUN_00766510 caller reference vector");
    detail::require_fun_00766510_finite(
        input.caller_cross_accumulator,
        "FUN_00766510 caller cross accumulator");
    detail::require_fun_00766510_finite(
        input.auxiliary_accumulator,
        "FUN_00766510 auxiliary accumulator");

    Fun00766510PrimaryResponseApplicationResult result{};
    result.transformed_response = transform_fun_007aefb0_refresh(
        input.body_frame,
        input.response_vector);

    result.body_accumulator = input.body_accumulator;
    apply_fun_007baa70_body_accumulator(
        result.body_accumulator,
        input.point_or_lever_arm,
        result.transformed_response);

    result.caller_cross_delta = detail::fun_00753650_cross(
        input.caller_reference_vector,
        result.transformed_response);
    result.caller_cross_accumulator = input.caller_cross_accumulator;
    result.auxiliary_accumulator = input.auxiliary_accumulator;
    for (std::size_t component = 0u; component < 3u; ++component) {
        result.caller_cross_accumulator[component] +=
            result.caller_cross_delta[component];
        result.auxiliary_accumulator[component] +=
            input.auxiliary_response[component];
    }

    detail::require_fun_00766510_finite(
        result.transformed_response,
        "FUN_00766510 transformed response");
    detail::require_fun_00766510_finite(
        result.body_accumulator.angular,
        "FUN_00766510 output BODY angular accumulator");
    detail::require_fun_00766510_finite(
        result.body_accumulator.linear,
        "FUN_00766510 output BODY linear accumulator");
    detail::require_fun_00766510_finite(
        result.caller_cross_delta,
        "FUN_00766510 caller cross delta");
    detail::require_fun_00766510_finite(
        result.caller_cross_accumulator,
        "FUN_00766510 output caller cross accumulator");
    detail::require_fun_00766510_finite(
        result.auxiliary_accumulator,
        "FUN_00766510 output auxiliary accumulator");
    return result;
}

}  // namespace shift::runtime::physics
