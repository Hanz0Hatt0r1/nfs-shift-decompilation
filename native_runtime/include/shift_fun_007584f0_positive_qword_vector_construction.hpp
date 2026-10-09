#pragma once

#include "shift_fun_007584f0_positive_qword_reduction.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007584f0PositiveQwordVectorConstructionFormat =
    "SHIFT.Fun007584f0PositiveQwordVectorConstruction/1";

inline constexpr std::uintptr_t kFun007584f0AxisTransformSpanStart = 0x0075850cu;
inline constexpr std::uintptr_t kFun007584f0AxisTransformSpanEnd = 0x0075853cu;
inline constexpr std::uintptr_t kFun007584f0LoopVectorConstructionStart = 0x0075858bu;
inline constexpr std::uintptr_t kFun007584f0LoopVectorConstructionEnd = 0x007586f9u;

inline constexpr std::size_t kFun007584f0SelectedBodyPointerOffset = 0x33a0u;
inline constexpr std::size_t kFun007584f0SelectedBodyTransformOffset = 0x00d4u;
inline constexpr std::size_t kFun007584f0SourceVector8a0Offset = 0x08a0u;
inline constexpr std::size_t kFun007584f0SourceVector888Offset = 0x0888u;
inline constexpr std::size_t kFun007584f0SourceVector8d0Offset = 0x08d0u;
inline constexpr std::size_t kFun007584f0SourceScalar818Offset = 0x0818u;
inline constexpr std::size_t kFun007584f0SourceScalar7f0Offset = 0x07f0u;
inline constexpr std::size_t kFun007584f0SourceScalar7e8Offset = 0x07e8u;
inline constexpr std::size_t kFun007584f0SourceLoadOffset = 0x0b38u;
inline constexpr std::size_t kFun007584f0SourceScalar900Offset = 0x0900u;
inline constexpr std::size_t kFun007584f0SourceLoopStride = 0x0a80u;
inline constexpr std::size_t kFun007584f0SourceLoopCount = 2u;

inline constexpr std::uintptr_t kFun007584f0IndexZeroFactorGlobal = 0x00aa9afcu;
inline constexpr std::uintptr_t kFun007584f0ScaleGlobal = 0x00aadd68u;
inline constexpr std::uintptr_t kFun007584f0AddGlobal = 0x00b09138u;
inline constexpr std::uintptr_t kFun007584f0CrossScaleGlobal = 0x00b03df8u;

using Fun007584f0BodyFrame3x3f = std::array<float, 9>;

struct Fun007584f0PositiveQwordVectorSourceInput {
    // All names below are positional/source-address names only. Physical field
    // meanings and ownership lifetimes remain unresolved.
    Fun007584f0BodyFrame3x3f selected_body_frame{};
    float cosine_f32 = 0.0f;
    float sine_f32 = 0.0f;
    std::size_t loop_index = 0u;
    Fun007584f0PositiveQwordVector vector_8a0{};
    Fun007584f0PositiveQwordVector vector_888{};
    Fun007584f0PositiveQwordVector vector_8d0{};
    double scalar_818 = 0.0;
    double scalar_7f0 = 0.0;
    double scalar_7e8 = 0.0;
    double load_b38 = 0.0;
    float scalar_900 = 0.0f;
    float index_zero_factor_aa9afc = 0.0f;
    double scale_aadd68 = 0.0;
    double add_b09138 = 0.0;
    double cross_scale_b03df8 = 0.0;
};

inline void validate_fun_007584f0_positive_qword_source_input(
    const Fun007584f0PositiveQwordVectorSourceInput& input) {
    if (input.loop_index >= kFun007584f0SourceLoopCount) {
        throw std::out_of_range(
            "FUN_007584f0 positive-qword loop index outside retail domain");
    }
    for (const float component : input.selected_body_frame) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(
                "FUN_007584f0 BODY frame component must be finite");
        }
    }
    if (!std::isfinite(input.cosine_f32) || !std::isfinite(input.sine_f32) ||
        !std::isfinite(input.scalar_818) || !std::isfinite(input.scalar_7f0) ||
        !std::isfinite(input.scalar_7e8) || !std::isfinite(input.load_b38) ||
        !std::isfinite(input.scalar_900) ||
        !std::isfinite(input.index_zero_factor_aa9afc) ||
        !std::isfinite(input.scale_aadd68) || !std::isfinite(input.add_b09138) ||
        !std::isfinite(input.cross_scale_b03df8)) {
        throw std::invalid_argument(
            "FUN_007584f0 positive-qword scalar source must be finite");
    }
    validate_fun_007584f0_positive_qword_vector(input.vector_8a0);
    validate_fun_007584f0_positive_qword_vector(input.vector_888);
    validate_fun_007584f0_positive_qword_vector(input.vector_8d0);
}

inline Fun007584f0PositiveQwordVector fun_007584f0_scale_vec3(
    const Fun007584f0PositiveQwordVector& value,
    double scalar) {
    return {value[0] * scalar, value[1] * scalar, value[2] * scalar};
}

inline Fun007584f0PositiveQwordVector fun_007584f0_add_vec3(
    const Fun007584f0PositiveQwordVector& left,
    const Fun007584f0PositiveQwordVector& right) {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

inline Fun007584f0PositiveQwordVector fun_007584f0_cross_vec3(
    const Fun007584f0PositiveQwordVector& left,
    const Fun007584f0PositiveQwordVector& right) {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

inline Fun007584f0PositiveQwordVector fun_007584f0_transform_vec3(
    const Fun007584f0BodyFrame3x3f& frame,
    const Fun007584f0PositiveQwordVector& value) {
    Fun007584f0PositiveQwordVector result{};
    for (std::size_t row = 0; row < 3u; ++row) {
        const std::size_t base = row * 3u;
        // FUN_007aefb0 accumulates components in retail order 1,0,2.
        double lane = static_cast<double>(frame[base + 1u]) * value[1u];
        lane += static_cast<double>(frame[base + 0u]) * value[0u];
        lane += static_cast<double>(frame[base + 2u]) * value[2u];
        result[row] = lane;
    }
    return result;
}

inline Fun007584f0PositiveQwordReductionInput
materialize_fun_007584f0_positive_qword_vectors(
    const Fun007584f0PositiveQwordVectorSourceInput& input) {
    validate_fun_007584f0_positive_qword_source_input(input);

    const Fun007584f0PositiveQwordVector local_axis =
        fun_007584f0_transform_vec3(
            input.selected_body_frame,
            Fun007584f0PositiveQwordVector{1.0, 0.0, 0.0});

    const Fun007584f0PositiveQwordVector a =
        fun_007584f0_transform_vec3(
            input.selected_body_frame,
            Fun007584f0PositiveQwordVector{
                0.0,
                static_cast<double>(input.cosine_f32),
                static_cast<double>(input.sine_f32),
            });

    const double loop_factor = input.loop_index == 0u
        ? static_cast<double>(input.index_zero_factor_aa9afc)
        : 1.0;

    const auto first_left = fun_007584f0_scale_vec3(
        input.vector_8a0,
        input.scalar_818 + input.add_b09138);
    const auto first_right = fun_007584f0_scale_vec3(
        input.vector_888,
        loop_factor * input.scale_aadd68);
    const auto first_sum = fun_007584f0_add_vec3(first_right, first_left);

    const auto second_a = fun_007584f0_scale_vec3(
        input.vector_8d0,
        input.load_b38);
    const auto second_b = fun_007584f0_scale_vec3(
        input.vector_8a0,
        input.scalar_7f0);
    const auto second_c = fun_007584f0_scale_vec3(
        input.vector_888,
        input.scalar_7e8);
    const auto second_partial = fun_007584f0_add_vec3(second_c, second_b);
    const auto second_sum = fun_007584f0_add_vec3(second_partial, second_a);

    auto b = fun_007584f0_cross_vec3(first_sum, second_sum);
    b = fun_007584f0_add_vec3(
        b,
        fun_007584f0_scale_vec3(
            input.vector_8d0,
            static_cast<double>(input.scalar_900)));

    const auto c = fun_007584f0_cross_vec3(
        fun_007584f0_scale_vec3(
            input.vector_8a0,
            input.cross_scale_b03df8),
        local_axis);

    return Fun007584f0PositiveQwordReductionInput{a, b, c};
}

}  // namespace shift::runtime::physics
