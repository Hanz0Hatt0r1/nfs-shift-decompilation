#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007584f0PositiveQwordReductionFormat =
    "SHIFT.Fun007584f0PositiveQwordReduction/1";

inline constexpr std::uintptr_t kFun007584f0PositiveQwordReductionStart =
    0x007586f9u;
inline constexpr std::uintptr_t kFun007584f0PositiveQwordStoreSite =
    0x00758731u;
inline constexpr std::uintptr_t kFun007584f0AlternateZeroStoreSite =
    0x0075873bu;
inline constexpr std::size_t kFun007584f0PositiveQwordVectorWidth = 3u;
inline constexpr std::size_t kFun007584f0PositiveQwordDestinationBase = 0x0d40u;
inline constexpr std::size_t kFun007584f0PositiveQwordWheelStride = 0x0a80u;
inline constexpr std::size_t kFun007584f0PositiveQwordWheelCount = 2u;

using Fun007584f0PositiveQwordVector =
    std::array<double, kFun007584f0PositiveQwordVectorWidth>;

struct Fun007584f0PositiveQwordReductionInput {
    // Semantic field names are not yet proven. Preserve only the positional
    // vec3 roles implied by the retail x87 reduction.
    Fun007584f0PositiveQwordVector a{};
    Fun007584f0PositiveQwordVector b{};
    Fun007584f0PositiveQwordVector c{};
};

inline void validate_fun_007584f0_positive_qword_vector(
    const Fun007584f0PositiveQwordVector& value) {
    for (const double component : value) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(
                "FUN_007584f0 positive-qword vector component must be finite");
        }
    }
}

inline double execute_fun_007584f0_positive_qword_reduction(
    const Fun007584f0PositiveQwordReductionInput& input) {
    validate_fun_007584f0_positive_qword_vector(input.a);
    validate_fun_007584f0_positive_qword_vector(input.b);
    validate_fun_007584f0_positive_qword_vector(input.c);

    // Preserve the recovered x87 accumulation order from
    // 0x007586f9..0x00758731 rather than replacing it with a generic dot helper.
    double numerator = input.a[1] * input.b[1];
    numerator += input.a[0] * input.b[0];
    numerator += input.a[2] * input.b[2];

    double denominator = input.a[1] * input.c[1];
    denominator += input.a[0] * input.c[0];
    denominator += input.a[2] * input.c[2];

    if (!std::isfinite(numerator) || !std::isfinite(denominator) ||
        denominator == 0.0) {
        throw std::invalid_argument(
            "FUN_007584f0 positive-qword reduction is not finite/divisible");
    }

    const double result = numerator / denominator;
    if (!std::isfinite(result)) {
        throw std::invalid_argument(
            "FUN_007584f0 positive-qword reduction result must be finite");
    }
    return result;
}

inline constexpr std::size_t fun_007584f0_positive_qword_destination_offset(
    std::size_t wheel_index) {
    return kFun007584f0PositiveQwordDestinationBase +
           wheel_index * kFun007584f0PositiveQwordWheelStride;
}

static_assert(kFun007584f0PositiveQwordReductionStart == 0x007586f9u);
static_assert(kFun007584f0PositiveQwordStoreSite == 0x00758731u);
static_assert(kFun007584f0AlternateZeroStoreSite == 0x0075873bu);
static_assert(fun_007584f0_positive_qword_destination_offset(0u) == 0x0d40u);
static_assert(fun_007584f0_positive_qword_destination_offset(1u) == 0x17c0u);

}  // namespace shift::runtime::physics
