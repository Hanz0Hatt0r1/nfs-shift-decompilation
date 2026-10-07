#pragma once

#include "shift_contact_outer_kernel.hpp"

#include <array>
#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007675f0BodyOwnedScalarsFormat =
    "SHIFT.Fun007675f0BodyOwnedScalars/1";

struct Fun007675f0BodyOwnedScalarsResult {
    std::array<float, 3> planar_direction{};
    std::array<float, 3> normalized_planar_motion{};
    std::array<float, 3> aligned_perpendicular{};
    float filtered_distance = 0.0f;
    float body_field_120 = 0.0f;
    float perpendicular_motion = 0.0f;
    float base_scalar = 0.0f;
    float alignment_scalar = 0.0f;
};

inline float fun_007675f0_source_f32(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
    const float result = static_cast<float>(value);
    if (!std::isfinite(result)) {
        throw std::invalid_argument(label);
    }
    return result;
}

inline float fun_007675f0_source_sqrt_f32(float value, const char* label) {
    if (!std::isfinite(value) || value < 0.0f) {
        throw std::invalid_argument(label);
    }
    return fun_007675f0_source_f32(
        std::sqrt(static_cast<double>(value)),
        label);
}

inline std::array<float, 3> fun_007675f0_source_cross_f32(
    const std::array<float, 3>& lhs,
    const std::array<float, 3>& rhs) {
    // FUN_0047bdb0 writes each component to f32 after the visible expression.
    return {
        fun_007675f0_source_f32(
            static_cast<double>(lhs[1]) * rhs[2] -
                static_cast<double>(lhs[2]) * rhs[1],
            "FUN_007675f0 cross X overflow"),
        fun_007675f0_source_f32(
            static_cast<double>(lhs[2]) * rhs[0] -
                static_cast<double>(lhs[0]) * rhs[2],
            "FUN_007675f0 cross Y overflow"),
        fun_007675f0_source_f32(
            static_cast<double>(rhs[1]) * lhs[0] -
                static_cast<double>(rhs[0]) * lhs[1],
            "FUN_007675f0 cross Z overflow"),
    };
}

inline std::array<float, 3> fun_007675f0_source_normalize_f32(
    const std::array<float, 3>& value) {
    // FUN_00442310 evaluates z*z + x*x + y*y, spills the sqrt to f32,
    // spills the reciprocal to f32, then stores all three scaled components.
    const float magnitude_sq = fun_007675f0_source_f32(
        static_cast<double>(value[2]) * value[2] +
            static_cast<double>(value[0]) * value[0] +
            static_cast<double>(value[1]) * value[1],
        "FUN_007675f0 normalized cross magnitude overflow");
    if (magnitude_sq == 0.0f) {
        return value;
    }
    const float magnitude = fun_007675f0_source_sqrt_f32(
        magnitude_sq,
        "FUN_007675f0 normalized cross magnitude invalid");
    const float inverse = fun_007675f0_source_f32(
        1.0 / static_cast<double>(magnitude),
        "FUN_007675f0 normalized cross reciprocal overflow");
    return {
        fun_007675f0_source_f32(
            static_cast<double>(inverse) * value[0],
            "FUN_007675f0 normalized cross X overflow"),
        fun_007675f0_source_f32(
            static_cast<double>(inverse) * value[1],
            "FUN_007675f0 normalized cross Y overflow"),
        fun_007675f0_source_f32(
            static_cast<double>(inverse) * value[2],
            "FUN_007675f0 normalized cross Z overflow"),
    };
}

inline Fun007675f0BodyOwnedScalarsResult
execute_fun_007675f0_body_owned_scalars(
    const ContactOuterVector3d& planar_delta,
    const Fun007675f0BodyMotion& motion,
    double filtered_distance_state,
    double body_field_120) {
    const float delta_x = fun_007675f0_source_f32(
        planar_delta[0], "FUN_007675f0 planar delta X is not source-f32 finite");
    const float delta_z = fun_007675f0_source_f32(
        planar_delta[2], "FUN_007675f0 planar delta Z is not source-f32 finite");
    const float distance_sq = fun_007675f0_source_f32(
        static_cast<double>(delta_x) * delta_x + 0.0 +
            static_cast<double>(delta_z) * delta_z,
        "FUN_007675f0 source planar distance square overflow");
    const float distance = fun_007675f0_source_sqrt_f32(
        distance_sq,
        "FUN_007675f0 source planar distance invalid");
    if (distance == 0.0f) {
        throw std::invalid_argument(
            "FUN_007675f0 body-owned scalars require non-zero planar distance");
    }
    const float inverse_distance = fun_007675f0_source_f32(
        1.0 / static_cast<double>(distance),
        "FUN_007675f0 source planar distance reciprocal overflow");

    Fun007675f0BodyOwnedScalarsResult result{};
    result.planar_direction = {
        fun_007675f0_source_f32(
            static_cast<double>(inverse_distance) * delta_x,
            "FUN_007675f0 planar direction X overflow"),
        0.0f,
        fun_007675f0_source_f32(
            static_cast<double>(inverse_distance) * delta_z,
            "FUN_007675f0 planar direction Z overflow"),
    };

    const float motion_x = fun_007675f0_source_f32(
        motion.speed_x, "FUN_007675f0 BODY0 speed X is not source-f32 finite");
    const float motion_z = fun_007675f0_source_f32(
        motion.speed_z, "FUN_007675f0 BODY0 speed Z is not source-f32 finite");
    const float speed_sq = fun_007675f0_source_f32(
        static_cast<double>(motion_x) * motion_x + 0.0 +
            static_cast<double>(motion_z) * motion_z,
        "FUN_007675f0 source BODY0 speed square overflow");
    const float speed = fun_007675f0_source_sqrt_f32(
        speed_sq,
        "FUN_007675f0 source BODY0 speed invalid");
    if (speed == 0.0f) {
        throw std::invalid_argument(
            "FUN_007675f0 body-owned scalars require non-zero BODY0 planar speed");
    }
    const float inverse_speed = fun_007675f0_source_f32(
        1.0 / static_cast<double>(speed),
        "FUN_007675f0 source BODY0 speed reciprocal overflow");
    result.normalized_planar_motion = {
        fun_007675f0_source_f32(
            static_cast<double>(inverse_speed) * motion_x,
            "FUN_007675f0 normalized BODY0 X overflow"),
        0.0f,
        fun_007675f0_source_f32(
            static_cast<double>(inverse_speed) * motion_z,
            "FUN_007675f0 normalized BODY0 Z overflow"),
    };

    constexpr std::array<float, 3> kSourceUp = {0.0f, 1.0f, 0.0f};
    result.aligned_perpendicular = fun_007675f0_source_normalize_f32(
        fun_007675f0_source_cross_f32(
            result.normalized_planar_motion,
            kSourceUp));

    float alignment_sign_test = fun_007675f0_source_f32(
        static_cast<double>(result.aligned_perpendicular[2]) *
                result.planar_direction[2] +
            static_cast<double>(result.aligned_perpendicular[1]) *
                result.planar_direction[1] +
            static_cast<double>(result.aligned_perpendicular[0]) *
                result.planar_direction[0],
        "FUN_007675f0 alignment sign-test overflow");
    if (alignment_sign_test < 0.0f) {
        for (float& component : result.aligned_perpendicular) {
            component = fun_007675f0_source_f32(
                static_cast<double>(component) * -1.0,
                "FUN_007675f0 aligned perpendicular sign flip overflow");
        }
    }
    result.alignment_scalar = fun_007675f0_source_f32(
        static_cast<double>(result.aligned_perpendicular[2]) *
                result.planar_direction[2] +
            static_cast<double>(result.aligned_perpendicular[0]) *
                result.planar_direction[0] +
            static_cast<double>(result.aligned_perpendicular[1]) *
                result.planar_direction[1],
        "FUN_007675f0 alignment scalar overflow");

    const auto transverse = fun_007675f0_source_cross_f32(
        kSourceUp,
        result.planar_direction);
    result.perpendicular_motion = fun_007675f0_source_f32(
        static_cast<double>(transverse[2]) * motion_z +
            static_cast<double>(transverse[1]) * 0.0 +
            static_cast<double>(transverse[0]) * motion_x,
        "FUN_007675f0 perpendicular BODY0 motion overflow");
    result.filtered_distance = fun_007675f0_source_f32(
        filtered_distance_state,
        "FUN_007675f0 filtered distance state is not source-f32 finite");
    if (result.filtered_distance == 0.0f) {
        throw std::invalid_argument(
            "FUN_007675f0 body-owned base scalar requires non-zero filtered distance");
    }
    result.body_field_120 = fun_007675f0_source_f32(
        body_field_120,
        "FUN_007675f0 BODY0+0x120 is not source-f32 finite");
    result.base_scalar = fun_007675f0_source_f32(
        ((static_cast<double>(result.perpendicular_motion) *
          result.perpendicular_motion) /
         static_cast<double>(result.filtered_distance)) *
            result.body_field_120,
        "FUN_007675f0 body-owned base scalar overflow");
    return result;
}

}  // namespace shift::runtime::physics
