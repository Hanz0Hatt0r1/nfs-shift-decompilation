#pragma once

#include "shift_fun_00713630_reference_source.hpp"

#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007584f0PositiveQwordTrigFormat =
    "SHIFT.Fun007584f0PositiveQwordTrig/1";

inline constexpr std::uintptr_t kFun007584f0TrigSpanStart = 0x00758560u;
inline constexpr std::uintptr_t kFun007584f0TrigSpanEnd = 0x0075858bu;
inline constexpr std::uintptr_t kFun007584f0CosineCallSite = 0x0075856fu;
inline constexpr std::uintptr_t kFun007584f0SineCallSite = 0x00758580u;
inline constexpr std::size_t kFun007584f0TrigSourceOffset = 0x0738u;
inline constexpr std::size_t kFun007584f0TrigWheelStride = 0x0a80u;
inline constexpr std::size_t kFun007584f0TrigWheelCount = 2u;

struct Fun007584f0PositiveQwordTrigResult {
    float angle_f32 = 0.0f;
    float cosine_f32 = 0.0f;
    float sine_f32 = 0.0f;
};

inline Fun007584f0PositiveQwordTrigResult
materialize_fun_007584f0_positive_qword_trig(double angle_f64) {
    if (!std::isfinite(angle_f64)) {
        throw std::invalid_argument(
            "FUN_007584f0 positive-qword trig source must be finite");
    }

    // Retail 0x00758560..0x0075856c loads qword +0x738, spills it to f32,
    // then reloads that f32 for both wrappers. Keep that narrowing explicit.
    const float angle_f32 = static_cast<float>(angle_f64);
    if (!std::isfinite(angle_f32)) {
        throw std::invalid_argument(
            "FUN_007584f0 positive-qword trig f32 spill overflow");
    }

    // Retail calls FCOS first (0x0075856f), spills to f32, then calls FSIN
    // second (0x00758580) from the same f32 angle. Reuse the already-proven
    // Phase748 x87 helpers and preserve that call order.
    const float cosine_f32 = fun_00713630_retail_cos_f32(angle_f32);
    const float sine_f32 = fun_00713630_retail_sin_f32(angle_f32);

    return Fun007584f0PositiveQwordTrigResult{
        angle_f32,
        cosine_f32,
        sine_f32,
    };
}

inline constexpr std::size_t fun_007584f0_trig_source_offset(
    std::size_t wheel_index) {
    return kFun007584f0TrigSourceOffset +
           wheel_index * kFun007584f0TrigWheelStride;
}

static_assert(kFun007584f0TrigSpanStart == 0x00758560u);
static_assert(kFun007584f0TrigSpanEnd == 0x0075858bu);
static_assert(kFun007584f0CosineCallSite == 0x0075856fu);
static_assert(kFun007584f0SineCallSite == 0x00758580u);
static_assert(fun_007584f0_trig_source_offset(0u) == 0x0738u);
static_assert(fun_007584f0_trig_source_offset(1u) == 0x11b8u);

}  // namespace shift::runtime::physics
