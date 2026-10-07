#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_fun_00765c40_load_terms.hpp"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kFun00769ef0Param3Format =
    "SHIFT.Fun00769ef0Param3/1";
inline constexpr std::size_t kFun00769ef0Body0Field120Offset = 0x120u;
// Exact f64 constant at PC retail 0x00b09148 (bits 0x40239eb851eb851f).
inline constexpr double kFun00769ef0Param3Gravity = 0x1.39eb851eb851fp+3;

struct Fun00769ef0Param3Result {
    double load_sum = 0.0;
    double denominator = 0.0;
    float quotient_f32 = 0.0f;
    float param_3 = 0.0f;
};

inline double fun_00769ef0_add64(double lhs, double rhs) {
    volatile double result = lhs + rhs;
    return result;
}

inline double fun_00769ef0_mul64(double lhs, double rhs) {
    volatile double result = lhs * rhs;
    return result;
}

inline double fun_00769ef0_div64(double lhs, double rhs) {
    volatile double result = lhs / rhs;
    return result;
}

inline float fun_00769ef0_retail_f32_spill(double value) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            "FUN_00769ef0 param_3 f32 spill source must be finite");
    }
#if defined(__i386__) || defined(__x86_64__)
    unsigned short old_control = 0u;
    const unsigned short retail_control = 0x027fu;
    float output = 0.0f;
    asm volatile("fnstcw %0" : "=m"(old_control));
    asm volatile("fldcw %0" : : "m"(retail_control));
    asm volatile("fldl %1; fstps %0" : "=m"(output) : "m"(value));
    asm volatile("fldcw %0" : : "m"(old_control));
    return output;
#else
    throw std::runtime_error(
        "FUN_00769ef0 retail f32 spill requires x87-capable x86 host");
#endif
}

inline float fun_00769ef0_clamp01_f32(float value) {
    if (value <= 0.0f) {
        return 0.0f;
    }
    if (value >= 1.0f) {
        return 1.0f;
    }
    return value;
}

inline double derive_fun_00769ef0_body0_field_120(
    const std::vector<std::uint8_t>& current_body_bytes) {
    if (current_body_bytes.size() < kBodyRecordSize ||
        current_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_00769ef0 param_3 requires complete persistent BODY records");
    }
    if (kFun00769ef0Body0Field120Offset > current_body_bytes.size() ||
        current_body_bytes.size() - kFun00769ef0Body0Field120Offset < sizeof(std::uint64_t)) {
        throw std::invalid_argument(
            "FUN_00769ef0 BODY0 +0x120 read exceeds persistent BODY record");
    }

    std::uint64_t bits = 0u;
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bits |= static_cast<std::uint64_t>(
                    current_body_bytes[kFun00769ef0Body0Field120Offset + byte])
            << (byte * 8u);
    }
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            "FUN_00769ef0 BODY0 +0x120 must be finite");
    }
    if (value == 0.0) {
        throw std::invalid_argument(
            "FUN_00769ef0 BODY0 +0x120 cannot be zero");
    }
    return value;
}

inline Fun00769ef0Param3Result execute_fun_00769ef0_param_3(
    const Fun00765c40LoadTerms& load_terms,
    double body_field_120) {
    validate_fun_00765c40_load_terms(load_terms);
    if (!std::isfinite(body_field_120)) {
        throw std::invalid_argument(
            "FUN_00769ef0 BODY0 +0x120 must be finite");
    }
    if (body_field_120 == 0.0) {
        throw std::invalid_argument(
            "FUN_00769ef0 BODY0 +0x120 cannot be zero");
    }

    // PC 0x00769f44 starts from load term 0, adds an exact f64 +0.0 constant,
    // then adds terms 1..3. Keep every source f64 operation boundary explicit.
    double load_sum = load_terms[0];
    load_sum = fun_00769ef0_add64(load_sum, 0.0);
    load_sum = fun_00769ef0_add64(load_sum, load_terms[1]);
    load_sum = fun_00769ef0_add64(load_sum, load_terms[2]);
    load_sum = fun_00769ef0_add64(load_sum, load_terms[3]);
    const double denominator = fun_00769ef0_mul64(
        body_field_120,
        kFun00769ef0Param3Gravity);
    if (!std::isfinite(denominator) || denominator == 0.0) {
        throw std::invalid_argument(
            "FUN_00769ef0 param_3 denominator must be finite and non-zero");
    }
    const double quotient = fun_00769ef0_div64(load_sum, denominator);
    if (!std::isfinite(quotient)) {
        throw std::invalid_argument(
            "FUN_00769ef0 param_3 quotient must be finite");
    }
    const float quotient_f32 = fun_00769ef0_retail_f32_spill(quotient);
    if (!std::isfinite(quotient_f32)) {
        throw std::invalid_argument(
            "FUN_00769ef0 param_3 f32 quotient must be finite");
    }

    Fun00769ef0Param3Result result{};
    result.load_sum = load_sum;
    result.denominator = denominator;
    result.quotient_f32 = quotient_f32;
    result.param_3 = fun_00769ef0_clamp01_f32(quotient_f32);
    return result;
}

}  // namespace shift::runtime::physics
