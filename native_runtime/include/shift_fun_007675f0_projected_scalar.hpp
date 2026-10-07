#pragma once

#include "shift_fun_007675f0_body_owned_scalars.hpp"
#include "shift_wheel_force_aggregate.hpp"

#include <array>
#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007675f0ProjectedScalarFormat =
    "SHIFT.Fun007675f0ProjectedScalar/1";

struct Fun007675f0ProjectedScalarResult {
    std::array<float, 3> planar_direction{};
    float aggregate_total_x = 0.0f;
    float aggregate_total_z = 0.0f;
    float projected_scalar = 0.0f;
};

inline Fun007675f0ProjectedScalarResult
execute_fun_007675f0_projected_scalar(
    const Fun00759c90AggregateResult& aggregate,
    const ContactOuterVector3d& planar_delta) {

    // PC FUN_007675f0 builds the X/Z direction through explicit f32 stores
    // before calling FUN_00759c90. Reproduce those stores rather than using the
    // higher-precision convenience direction kept by the outer-kernel result.
    const float delta_x = fun_007675f0_source_f32(
        planar_delta[0],
        "FUN_007675f0 projected-scalar delta X is not source-f32 finite");
    const float delta_z = fun_007675f0_source_f32(
        planar_delta[2],
        "FUN_007675f0 projected-scalar delta Z is not source-f32 finite");
    const float distance_sq = fun_007675f0_source_f32(
        static_cast<double>(delta_x) * delta_x + 0.0 +
            static_cast<double>(delta_z) * delta_z,
        "FUN_007675f0 projected-scalar distance square overflow");
    const float distance = fun_007675f0_source_sqrt_f32(
        distance_sq,
        "FUN_007675f0 projected-scalar distance invalid");
    if (distance == 0.0f) {
        throw std::invalid_argument(
            "FUN_007675f0 projected scalar requires non-zero planar distance");
    }
    const float inverse_distance = fun_007675f0_source_f32(
        1.0 / static_cast<double>(distance),
        "FUN_007675f0 projected-scalar reciprocal overflow");

    Fun007675f0ProjectedScalarResult result{};
    result.planar_direction = {
        fun_007675f0_source_f32(
            static_cast<double>(inverse_distance) * delta_x,
            "FUN_007675f0 projected-scalar direction X overflow"),
        0.0f,
        fun_007675f0_source_f32(
            static_cast<double>(inverse_distance) * delta_z,
            "FUN_007675f0 projected-scalar direction Z overflow"),
    };

    // 0x007677b4 and 0x007677bd spill aggregate total X/Z f64 lanes to f32.
    result.aggregate_total_x = fun_007675f0_source_f32(
        aggregate.total[0],
        "FUN_007675f0 aggregate total X is not source-f32 finite");
    result.aggregate_total_z = fun_007675f0_source_f32(
        aggregate.total[2],
        "FUN_007675f0 aggregate total Z is not source-f32 finite");

    // 0x007677c6..0x007677df keeps the two products/additions in x87 and
    // performs one final f32 store. Products of f32 operands and their sum fit
    // exactly in binary64, so this expression preserves the visible x87 result
    // before the final source-f32 spill. The middle term is explicitly zero in
    // retail machine code.
    result.projected_scalar = fun_007675f0_source_f32(
        static_cast<double>(result.aggregate_total_x) *
                result.planar_direction[0] +
            0.0 +
            static_cast<double>(result.aggregate_total_z) *
                result.planar_direction[2],
        "FUN_007675f0 projected scalar overflow");
    return result;
}

}  // namespace shift::runtime::physics
