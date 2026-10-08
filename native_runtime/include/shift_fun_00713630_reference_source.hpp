#pragma once

#include "shift_fun_00766510_shared_reference_vector.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00713630ReferenceSourceFormat =
    "SHIFT.Fun00713630ReferenceSource/1";
inline constexpr const char* kFun00712940ReferenceAggregateFormat =
    "SHIFT.Fun00712940ReferenceAggregate/1";

inline constexpr std::size_t kFun00713630ManagerArrayOffset = 0x140u;
inline constexpr std::size_t kFun00713630ManagerCountOffset = 0x144u;
inline constexpr std::size_t kFun007144a0CadenceCounterOffset = 0x158u;
inline constexpr std::size_t kFun00713630ManagerRecordStride = 0x1fa0u;
inline constexpr std::size_t kFun00713630ManagerRecordActiveOffset = 0x4eu;
inline constexpr std::size_t kFun00713630ParticipantSampleBaseOffset = 0x2b10u;
inline constexpr std::size_t kFun00713630ParticipantSampleCount = 3u;
inline constexpr std::size_t kFun00713630ParticipantSampleStride = 0x0cu;
inline constexpr std::size_t kFun00713630ParticipantAngleOffset = 0x4b0u;
inline constexpr std::size_t kFun00713630ParticipantPrimaryOutputOffset = 0x2128u;
inline constexpr std::size_t kFun00713630ParticipantSecondaryOutputOffset = 0x212cu;

using Fun00712940ReferenceRecord = std::array<float, 3>;

struct Fun00712940ReferenceConfig {
    // Source-global inputs are intentionally named only by their observed role.
    // Phase748 does not infer physical units or freeze runtime values.
    float record_0_limit = 0.0f;       // DAT_00c12eec
    float record_0_scale = 0.0f;       // DAT_00c12ef4
    float record_0_offset = 0.0f;      // DAT_00c12ef0
    float record_2_ramp_begin = 0.0f;  // DAT_00c12ee0
    float record_2_ramp_end = 0.0f;    // DAT_00c12ee4
    float record_2_divisor = 0.0f;     // DAT_00c12ee8
    float final_output_scale = 0.0f;   // DAT_00c12f04
};

struct Fun00712940ReferenceAggregateResult {
    float primary = 0.0f;
    float secondary = 0.0f;
};

struct Fun00713630ReferenceSourceInput {
    std::array<Fun00712940ReferenceRecord, kFun00713630ParticipantSampleCount>
        samples{};
    float participant_angle = 0.0f;
    Fun00712940ReferenceConfig config{};
};

struct Fun00713630ReferenceSourceResult {
    Fun00712940ReferenceAggregateResult aggregate{};
    float final_scale = 0.0f;
    float sin_angle = 0.0f;
    float cos_angle = 0.0f;
    Fun00766510ParticipantReferenceSource3f participant_source{};
};

inline float fun_00713630_source_f32(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
    const float output = static_cast<float>(value);
    if (!std::isfinite(output)) {
        throw std::invalid_argument(label);
    }
    return output;
}

inline void validate_fun_00712940_reference_config(
    const Fun00712940ReferenceConfig& config) {
    const std::array<float, 7> values = {
        config.record_0_limit,
        config.record_0_scale,
        config.record_0_offset,
        config.record_2_ramp_begin,
        config.record_2_ramp_end,
        config.record_2_divisor,
        config.final_output_scale,
    };
    for (const float value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00712940 reference config contains non-finite f32");
        }
    }
    if (config.record_0_limit == 0.0f) {
        throw std::invalid_argument(
            "FUN_00712940 record_0_limit must be non-zero for retail divide");
    }
    if (config.record_2_divisor == 0.0f) {
        throw std::invalid_argument(
            "FUN_00712940 record_2_divisor must be non-zero for retail divide");
    }
    if (config.record_2_ramp_begin != config.record_2_ramp_end &&
        !std::isfinite(
            static_cast<double>(config.record_2_ramp_end) -
            static_cast<double>(config.record_2_ramp_begin))) {
        throw std::invalid_argument(
            "FUN_00712940 record_2 ramp range is invalid");
    }
}

inline Fun00712940ReferenceAggregateResult
execute_fun_00712940_reference_aggregate(
    const std::array<Fun00712940ReferenceRecord,
                     kFun00713630ParticipantSampleCount>& samples,
    const Fun00712940ReferenceConfig& config) {
    validate_fun_00712940_reference_config(config);

    Fun00712940ReferenceAggregateResult result{};
    for (const auto& sample : samples) {
        for (const float lane : sample) {
            if (!std::isfinite(lane)) {
                throw std::invalid_argument(
                    "FUN_00712940 reference sample contains non-finite f32");
            }
        }

        const float x = sample[0];
        const float y = sample[1];
        const float z = sample[2];
        if (config.record_0_limit <= x) {
            continue;
        }

        // PC 0x0071295e..0x00712968 performs the arithmetic in x87 and then
        // explicitly spills the combined expression to f32.
        const float gate_denominator = fun_00713630_source_f32(
            (static_cast<double>(x) * static_cast<double>(config.record_0_scale)) /
                    static_cast<double>(config.record_0_limit) +
                static_cast<double>(config.record_0_offset),
            "FUN_00712940 gate denominator overflow");
        if (gate_denominator == 0.0f) {
            continue;
        }

        const float gate_ratio = fun_00713630_source_f32(
            (static_cast<double>(gate_denominator) -
             std::fabs(static_cast<double>(y))) /
                static_cast<double>(gate_denominator),
            "FUN_00712940 gate ratio overflow");
        if (!(gate_ratio > 0.0f)) {
            continue;
        }

        const float record_0_ratio = fun_00713630_source_f32(
            (static_cast<double>(config.record_0_limit) -
             static_cast<double>(x)) /
                static_cast<double>(config.record_0_limit),
            "FUN_00712940 record_0 ratio overflow");
        const float sqrt_gate = fun_00713630_source_f32(
            std::sqrt(static_cast<double>(gate_ratio)),
            "FUN_00712940 sqrt gate overflow");
        const float squared_record_0_ratio = fun_00713630_source_f32(
            static_cast<double>(record_0_ratio) *
                static_cast<double>(record_0_ratio),
            "FUN_00712940 squared record_0 ratio overflow");

        float ramp = 1.0f;
        if (z < config.record_2_ramp_begin) {
            ramp = 0.0f;
        } else if (z < config.record_2_ramp_end) {
            const double denominator =
                static_cast<double>(config.record_2_ramp_end) -
                static_cast<double>(config.record_2_ramp_begin);
            if (denominator == 0.0) {
                throw std::invalid_argument(
                    "FUN_00712940 active record_2 ramp has zero span");
            }
            ramp = fun_00713630_source_f32(
                (static_cast<double>(z) -
                 static_cast<double>(config.record_2_ramp_begin)) /
                    denominator,
                "FUN_00712940 record_2 ramp overflow");
        }

        // The source-visible value is spilled to f32 before both caller
        // accumulators are updated.
        const float contribution = fun_00713630_source_f32(
            static_cast<double>(ramp) *
                static_cast<double>(sqrt_gate) *
                static_cast<double>(squared_record_0_ratio),
            "FUN_00712940 contribution overflow");
        result.primary = fun_00713630_source_f32(
            static_cast<double>(result.primary) +
                static_cast<double>(contribution),
            "FUN_00712940 primary accumulation overflow");

        const float record_2_ratio = fun_00713630_source_f32(
            static_cast<double>(z) /
                static_cast<double>(config.record_2_divisor),
            "FUN_00712940 record_2 divisor ratio overflow");
        const float secondary_multiplier =
            record_2_ratio < 1.0f ? record_2_ratio : 1.0f;
        result.secondary = fun_00713630_source_f32(
            static_cast<double>(result.secondary) +
                static_cast<double>(contribution) *
                    static_cast<double>(secondary_multiplier),
            "FUN_00712940 secondary accumulation overflow");
    }
    return result;
}

inline float fun_00713630_retail_sin_f32(float angle) {
    if (!std::isfinite(angle)) {
        throw std::invalid_argument("FUN_00713630 angle is non-finite");
    }
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    asm volatile("flds %1; fsin; fstps %0" : "=m"(output) : "m"(angle));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_00713630 retail FSIN path requires x87-capable x86 host");
#endif
}

inline float fun_00713630_retail_cos_f32(float angle) {
    if (!std::isfinite(angle)) {
        throw std::invalid_argument("FUN_00713630 angle is non-finite");
    }
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    asm volatile("flds %1; fcos; fstps %0" : "=m"(output) : "m"(angle));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_00713630 retail FCOS path requires x87-capable x86 host");
#endif
}

inline Fun00713630ReferenceSourceResult execute_fun_00713630_reference_source(
    const Fun00713630ReferenceSourceInput& input) {
    if (!std::isfinite(input.participant_angle)) {
        throw std::invalid_argument(
            "FUN_00713630 participant +0x4b0 angle is non-finite");
    }

    Fun00713630ReferenceSourceResult result{};
    result.aggregate = execute_fun_00712940_reference_aggregate(
        input.samples,
        input.config);

    // PC 0x007136d5..0x007136e1 multiplies two f32 operands in x87 and
    // explicitly spills to f32 before the trig calls.
    result.final_scale = fun_00713630_source_f32(
        static_cast<double>(input.config.final_output_scale) *
            static_cast<double>(result.aggregate.secondary),
        "FUN_00713630 final scale overflow");
    result.sin_angle = fun_00713630_retail_sin_f32(input.participant_angle);
    result.cos_angle = fun_00713630_retail_cos_f32(input.participant_angle);

    // PC calls FSIN wrapper first for X and FCOS wrapper second for Z, then
    // negates each product and stores all three lanes as f32.
    result.participant_source = {
        fun_00713630_source_f32(
            -static_cast<double>(result.sin_angle) *
                static_cast<double>(result.final_scale),
            "FUN_00713630 participant source X overflow"),
        0.0f,
        fun_00713630_source_f32(
            -static_cast<double>(result.cos_angle) *
                static_cast<double>(result.final_scale),
            "FUN_00713630 participant source Z overflow"),
    };
    return result;
}

inline bool fun_007144a0_should_refresh_reference_source(int manager_counter) {
    return manager_counter % 3 == 0;
}

}  // namespace shift::runtime::physics
