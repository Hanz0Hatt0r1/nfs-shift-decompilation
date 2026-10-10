#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007c5a20TrigRecordMaterializerFormat =
    "SHIFT.Fun007c5a20TrigRecordMaterializer/1";

inline constexpr std::uintptr_t kFun007c5a20MaterializerStart = 0x007c5a20u;
inline constexpr std::uintptr_t kFun007c5a20MaterializerEnd = 0x007c5ab8u;
inline constexpr std::uintptr_t kFun007bf790SelectedCallsStart = 0x007bf983u;
inline constexpr std::uintptr_t kFun007bf790SelectedCallsEnd = 0x007bf9d3u;
inline constexpr double kFun007c5a20SelectedTrigScale =
    0.017453292519943295;

inline constexpr std::size_t kFun007bf790LoadObjectOffset = 0x0fe8u;
inline constexpr std::array<std::size_t, 2> kFun007bf790SourceVectorOffsets{
    0x11d0u,
    0x11e8u,
};
inline constexpr std::array<std::size_t, 2> kFun007bf790SelectorOffsets{
    0x13c0u,
    0x13c8u,
};
inline constexpr std::array<std::size_t, 2> kFun007bf790DestinationRecordOffsets{
    0x1188u,
    0x11d8u,
};

using Fun007c5a20SourceVector = std::array<double, 3>;

struct Fun007c5a20TrigRecordMaterializerInput {
    Fun007c5a20SourceVector source{};
    double selector = 0.0;
    std::int32_t previous_count = 0;
};

struct Fun007c5a20TrigRecordMaterializerResult {
    double base_value = 0.0;
    double slope_value = 0.0;
    std::int32_t count = 0;
    std::int32_t current_index = 0;
};

inline std::int32_t fun_007c5a20_truncate_to_i32(double value) {
    if (!std::isfinite(value) ||
        value < static_cast<double>(std::numeric_limits<std::int32_t>::min()) ||
        value > static_cast<double>(std::numeric_limits<std::int32_t>::max())) {
        throw std::invalid_argument(
            "FUN_007c5a20 integer-conversion input outside valid i32 domain");
    }
    return static_cast<std::int32_t>(value);
}

inline Fun007c5a20TrigRecordMaterializerResult
materialize_fun_007c5a20_trig_record(
    const Fun007c5a20TrigRecordMaterializerInput& input) {
    for (const double component : input.source) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(
                "FUN_007c5a20 trig record source component must be finite");
        }
    }
    if (!std::isfinite(input.selector)) {
        throw std::invalid_argument(
            "FUN_007c5a20 trig record selector must be finite");
    }

    Fun007c5a20TrigRecordMaterializerResult result{};
    result.base_value = input.source[0];
    result.slope_value = input.source[1];
    result.count = input.previous_count;

    const double magnitude_squared =
        input.source[1] * input.source[1] +
        input.source[0] * input.source[0] +
        input.source[2] * input.source[2];
    if (!std::isfinite(magnitude_squared)) {
        throw std::invalid_argument(
            "FUN_007c5a20 trig record source magnitude overflow");
    }

    // Retail updates count and scales only when the three-qword source is
    // nonzero. Otherwise destination count survives from its previous state.
    if (magnitude_squared > 0.0) {
        result.count = fun_007c5a20_truncate_to_i32(input.source[2]);
        result.base_value *= kFun007c5a20SelectedTrigScale;
        result.slope_value *= kFun007c5a20SelectedTrigScale;
    }

    std::int32_t selected = fun_007c5a20_truncate_to_i32(input.selector);
    if (result.count < 1 || selected < 0) {
        selected = 0;
    } else if (selected >= result.count) {
        selected = result.count - 1;
    }
    result.current_index = selected;

    if (!std::isfinite(result.base_value) || !std::isfinite(result.slope_value)) {
        throw std::invalid_argument(
            "FUN_007c5a20 trig record scaled qword result must be finite");
    }
    return result;
}

static_assert(kFun007c5a20MaterializerStart == 0x007c5a20u);
static_assert(kFun007c5a20MaterializerEnd == 0x007c5ab8u);
static_assert(kFun007bf790SelectedCallsStart == 0x007bf983u);
static_assert(kFun007bf790SelectedCallsEnd == 0x007bf9d3u);
static_assert(kFun007bf790SourceVectorOffsets[0] == 0x11d0u);
static_assert(kFun007bf790SourceVectorOffsets[1] == 0x11e8u);
static_assert(kFun007bf790SelectorOffsets[0] == 0x13c0u);
static_assert(kFun007bf790SelectorOffsets[1] == 0x13c8u);

}  // namespace shift::runtime::physics
