#pragma once

#include "shift_fun_00769640_trig_source_writer.hpp"
#include "shift_fun_00901310_cvttsd2si.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {

inline constexpr const char* kFun007bf790CasterRecordMaterializationFormat =
    "SHIFT.Fun007bf790CasterRecordMaterialization/1";

inline constexpr std::uintptr_t kFun007bf790CasterCallerSpanStart = 0x007bf983u;
inline constexpr std::uintptr_t kFun007bf790CasterCallerSpanEnd = 0x007bf9d3u;
inline constexpr std::uintptr_t kFun007c5a20RecordMaterializerStart = 0x007c5a20u;
inline constexpr std::uintptr_t kFun007c5a20RecordMaterializerEnd = 0x007c5abau;
inline constexpr std::uintptr_t kFun00901310IntegerConversionBoundary = 0x00901310u;

inline constexpr std::size_t kFun007bf790LeftCasterRangeOffset = 0x01e8u;
inline constexpr std::size_t kFun007bf790LeftCasterSettingOffset = 0x03d8u;
inline constexpr std::size_t kFun007bf790RightCasterRangeOffset = 0x0200u;
inline constexpr std::size_t kFun007bf790RightCasterSettingOffset = 0x03e0u;
inline constexpr std::size_t kFun007bf790LeftCasterRecordRelativeOffset = 0x1188u;
inline constexpr std::size_t kFun007bf790RightCasterRecordRelativeOffset = 0x11d8u;
inline constexpr double kFun007bf790CasterDegreesToRadians =
    0.017453292519943295;

using Fun007bf790CasterRange = std::array<double, 3>;

struct Fun007bf790CasterConfigInput {
    Fun007bf790CasterRange range{};
    double setting = 0.0;
    // FUN_007c5a20 leaves record+0x10 untouched when range length is zero.
    // Keep that pre-call state explicit instead of inventing initialization.
    std::int32_t prior_count = 0;
};

struct Fun007bf790CasterRecordResult {
    double base_value = 0.0;
    double slope_value = 0.0;
    std::int32_t count = 0;
    std::int32_t coefficient = 0;
};

struct Fun007bf790CasterPairInput {
    Fun007bf790CasterConfigInput left{};
    Fun007bf790CasterConfigInput right{};
};

struct Fun007bf790CasterPairResult {
    Fun007bf790CasterRecordResult left{};
    Fun007bf790CasterRecordResult right{};
};

inline void validate_fun_007bf790_caster_config(
    const Fun007bf790CasterConfigInput& input) {
    for (const double component : input.range) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(
                "FUN_007bf790 caster range component must be finite");
        }
    }
    if (!std::isfinite(input.setting)) {
        throw std::invalid_argument(
            "FUN_007bf790 caster setting must be finite");
    }
}

template <typename IntegerConversionBoundary>
inline Fun007bf790CasterRecordResult
materialize_fun_007c5a20_caster_record(
    const Fun007bf790CasterConfigInput& input,
    IntegerConversionBoundary&& convert_to_integer) {
    validate_fun_007bf790_caster_config(input);

    Fun007bf790CasterRecordResult result{};
    result.base_value = input.range[0];
    result.slope_value = input.range[1];
    result.count = input.prior_count;

    // Retail 0x007c5a33..0x007c5a58 accumulates y^2 + x^2 + z^2 and compares
    // against the qword zero constant at 0x00aadd68.
    double range_norm_squared = input.range[1] * input.range[1];
    range_norm_squared += input.range[0] * input.range[0];
    range_norm_squared += input.range[2] * input.range[2];

    if (range_norm_squared > 0.0) {
        result.count = static_cast<std::int32_t>(
            convert_to_integer(input.range[2]));
        result.base_value *= kFun007bf790CasterDegreesToRadians;
        result.slope_value *= kFun007bf790CasterDegreesToRadians;
    }

    std::int32_t requested = static_cast<std::int32_t>(
        convert_to_integer(input.setting));
    if (result.count < 1 || requested < 0) {
        requested = 0;
    } else if (requested >= result.count) {
        requested = result.count - 1;
    }
    result.coefficient = requested;

    if (!std::isfinite(result.base_value) ||
        !std::isfinite(result.slope_value)) {
        throw std::invalid_argument(
            "FUN_007c5a20 caster record result must remain finite");
    }
    return result;
}

template <typename IntegerConversionBoundary>
inline Fun007bf790CasterPairResult
materialize_fun_007bf790_caster_records(
    const Fun007bf790CasterPairInput& input,
    IntegerConversionBoundary&& convert_to_integer) {
    // Preserve the retail caller order: left record +0x1188 first, then right
    // record +0x11d8. The conversion boundary is therefore observed in the
    // same left-count/left-setting/right-count/right-setting sequence for
    // non-zero ranges.
    auto&& conversion = convert_to_integer;
    const auto left = materialize_fun_007c5a20_caster_record(
        input.left, conversion);
    const auto right = materialize_fun_007c5a20_caster_record(
        input.right, conversion);
    return {left, right};
}

// Native value-path overloads. Keep the callback forms above for historical
// tests and explicit instrumentation, while production P2.4 callers can use
// the recovered FUN_00901310 value semantics directly.
inline Fun007bf790CasterRecordResult
materialize_fun_007c5a20_caster_record(
    const Fun007bf790CasterConfigInput& input) {
    return materialize_fun_007c5a20_caster_record(
        input,
        [](double value) {
            return execute_fun_00901310_cvttsd2si(value);
        });
}

inline Fun007bf790CasterPairResult
materialize_fun_007bf790_caster_records(
    const Fun007bf790CasterPairInput& input) {
    return materialize_fun_007bf790_caster_records(
        input,
        [](double value) {
            return execute_fun_00901310_cvttsd2si(value);
        });
}

inline Fun00769640TrigSourceWriterInput
fun_007bf790_caster_record_to_trig_writer_input(
    const Fun007bf790CasterRecordResult& record) {
    return {
        record.base_value,
        record.slope_value,
        record.coefficient,
    };
}

static_assert(kFun007bf790CasterCallerSpanStart == 0x007bf983u);
static_assert(kFun007bf790CasterCallerSpanEnd == 0x007bf9d3u);
static_assert(kFun007c5a20RecordMaterializerStart == 0x007c5a20u);
static_assert(kFun007c5a20RecordMaterializerEnd == 0x007c5abau);
static_assert(kFun007bf790LeftCasterRangeOffset == 0x01e8u);
static_assert(kFun007bf790RightCasterRangeOffset == 0x0200u);
static_assert(kFun007bf790LeftCasterRecordRelativeOffset == 0x1188u);
static_assert(kFun007bf790RightCasterRecordRelativeOffset == 0x11d8u);

}  // namespace shift::runtime::physics
