#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007584f0TrigBoundaryFormat =
    "SHIFT.Fun007584f0TrigBoundary/1";

inline constexpr std::uintptr_t kFun007584f0TrigCallerStart = 0x00758560u;
inline constexpr std::uintptr_t kFun007584f0TrigCallerEnd = 0x0075858bu;
inline constexpr std::size_t kFun007584f0TrigSourceOffset = 0x0738u;
inline constexpr std::uintptr_t kFun007584f0CosineWrapper = 0x00900b10u;
inline constexpr std::uintptr_t kFun007584f0SineWrapper = 0x00900c40u;

// The exact CRT/x87 wrappers retain their own FP-environment and range-reduction
// behavior. P2.4 owns only the recovered caller-side f64 -> f32 narrowing,
// cosine-before-sine order, and the f32 values consumed by vector construction.
using Fun007584f0TrigWrapper = std::function<float(float)>;

struct Fun007584f0TrigBoundaryResult {
    float source_f32 = 0.0f;
    float cosine_f32 = 0.0f;
    float sine_f32 = 0.0f;
    std::size_t cosine_call_count = 0u;
    std::size_t sine_call_count = 0u;
};

inline Fun007584f0TrigBoundaryResult execute_fun_007584f0_trig_boundary(
    double source_qword,
    const Fun007584f0TrigWrapper& cosine_wrapper,
    const Fun007584f0TrigWrapper& sine_wrapper) {
    if (!std::isfinite(source_qword)) {
        throw std::invalid_argument(
            "FUN_007584f0 trig source qword must be finite");
    }
    if (!cosine_wrapper || !sine_wrapper) {
        throw std::invalid_argument(
            "FUN_007584f0 trig wrappers must both be provided");
    }

    const float source_f32 = static_cast<float>(source_qword);
    if (!std::isfinite(source_f32)) {
        throw std::invalid_argument(
            "FUN_007584f0 trig source must remain finite after f32 narrowing");
    }

    Fun007584f0TrigBoundaryResult result{};
    result.source_f32 = source_f32;

    result.cosine_f32 = cosine_wrapper(source_f32);
    result.cosine_call_count = 1u;
    if (!std::isfinite(result.cosine_f32)) {
        throw std::invalid_argument(
            "FUN_007584f0 cosine wrapper returned non-finite f32");
    }

    result.sine_f32 = sine_wrapper(source_f32);
    result.sine_call_count = 1u;
    if (!std::isfinite(result.sine_f32)) {
        throw std::invalid_argument(
            "FUN_007584f0 sine wrapper returned non-finite f32");
    }

    return result;
}

static_assert(kFun007584f0TrigCallerStart == 0x00758560u);
static_assert(kFun007584f0TrigCallerEnd == 0x0075858bu);
static_assert(kFun007584f0TrigSourceOffset == 0x0738u);
static_assert(kFun007584f0CosineWrapper == 0x00900b10u);
static_assert(kFun007584f0SineWrapper == 0x00900c40u);

}  // namespace shift::runtime::physics
