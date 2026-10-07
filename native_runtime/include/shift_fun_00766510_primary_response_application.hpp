#pragma once

#include "shift_body_accumulator_primitives.hpp"
#include "shift_constraint_sample_refresh.hpp"
#include "shift_wheel_contact_response.hpp"

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510PrimaryResponseApplicationFormat =
    "SHIFT.Fun00766510PrimaryResponseApplication/2";
inline constexpr std::size_t kFun00766510BodyPointerOffset = 0x33a0u;
inline constexpr std::size_t kFun00766510BodyBasisOffset = 0xd4u;
inline constexpr std::size_t kFun00766510ApplicationPointOffset = 0x38f0u;
inline constexpr std::size_t kFun00766510ResponseTableOffset = 0x3950u;
inline constexpr std::size_t kFun00766510ResponseGainOutputOffset = 0x39d0u;
inline constexpr std::array<std::size_t, 3> kFun00766510CallerAccumulatorOffsets = {
    0x40a0u,
    0x40a8u,
    0x40b0u,
};
inline constexpr std::size_t kFun00766510SelectedBmwBodyIndex = 0u;

struct Fun00766510PrimaryResponseApplicationInput {
    ConstraintRefreshFrame3f body_frame{};
    BodyAccumulatorState body_accumulator{};
    BodyAccumulatorVector3d application_point{};
    WheelContactResponse response{};
};

struct Fun00766510PrimaryResponseApplicationResult {
    WheelContactVector3d response_vector{};
    WheelContactVector3d transformed_response{};
    BodyAccumulatorState body_accumulator{};

    // Retail immediately calls FUN_00753650 with the same application point
    // and transformed response, then accumulates that returned vector into
    // HDVehicle+0x40a0/+0x40a8/+0x40b0. Keep the source call explicit instead
    // of reconstructing the value from a later BODY accumulator difference.
    BodyAccumulatorVector3d caller_accumulator_delta{};
};

inline Fun00766510PrimaryResponseApplicationResult
execute_fun_00766510_primary_response_application(
    const Fun00766510PrimaryResponseApplicationInput& input) {

    Fun00766510PrimaryResponseApplicationResult result{};
    result.response_vector = input.response.response_vector;
    result.transformed_response = transform_fun_007aefb0_refresh(
        input.body_frame,
        result.response_vector);
    result.caller_accumulator_delta = execute_fun_00753650_cross_product(
        input.application_point,
        result.transformed_response);
    result.body_accumulator = input.body_accumulator;
    apply_fun_007baa70_body_accumulator(
        result.body_accumulator,
        input.application_point,
        result.transformed_response);
    return result;
}

}  // namespace shift::runtime::physics
