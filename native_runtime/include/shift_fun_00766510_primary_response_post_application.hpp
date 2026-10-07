#pragma once

#include "shift_fun_00766510_primary_response_application.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510PrimaryResponsePostApplicationFormat =
    "SHIFT.Fun00766510PrimaryResponsePostApplication/1";
inline constexpr std::size_t kFun00766510CallerReferenceVectorOffset = 0x3b08u;
inline constexpr std::size_t kFun00766510CallerCrossAccumulatorXOffset = 0x40a0u;
inline constexpr std::size_t kFun00766510CallerCrossAccumulatorYOffset = 0x40a8u;
inline constexpr std::size_t kFun00766510CallerCrossAccumulatorZOffset = 0x40b0u;
inline constexpr std::uint16_t kFun00753650RetailX87ControlWord = 0x027fu;

struct Fun00766510PrimaryResponsePostApplicationInput {
    // local_108 at the Phase743 entry. Its earlier source-visible producer uses
    // HDVehicle+0x3b08, but ownership of that producer stays explicit here.
    BodyAccumulatorVector3d caller_reference_vector{};

    // local_120, already produced by Phase742's FUN_007aefb0 transform.
    BodyAccumulatorVector3d transformed_response{};

    // Persistent caller triplet HDVehicle+0x40a0/+0x40a8/+0x40b0.
    BodyAccumulatorVector3d caller_cross_accumulator{};

    // local_78/local_70/local_68 from the current FUN_007551e0 call.
    WheelContactVector3d auxiliary_response{};

    // local_c0/local_b8/local_b0 accumulated by earlier FUN_00766510 branches.
    WheelContactVector3d auxiliary_accumulator{};
};

struct Fun00766510PrimaryResponsePostApplicationResult {
    BodyAccumulatorVector3d caller_cross_delta{};
    BodyAccumulatorVector3d caller_cross_accumulator{};
    WheelContactVector3d auxiliary_accumulator{};
};

namespace detail {

template <typename Range>
inline void require_fun_00766510_post_finite(
    const Range& values,
    const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

#if defined(__i386__) || defined(__x86_64__)

struct ScopedFun00753650RetailX87ControlWord {
    std::uint16_t saved = 0u;

    ScopedFun00753650RetailX87ControlWord() {
        asm volatile("fnstcw %0" : "=m"(saved));
        asm volatile("fldcw %0" : : "m"(kFun00753650RetailX87ControlWord));
    }

    ~ScopedFun00753650RetailX87ControlWord() {
        asm volatile("fldcw %0" : : "m"(saved));
    }
};

inline BodyAccumulatorVector3d fun_00753650_pc_x87_cross(
    const BodyAccumulatorVector3d& left,
    const BodyAccumulatorVector3d& right) {
    ScopedFun00753650RetailX87ControlWord control{};
    BodyAccumulatorVector3d output{};

    // Exact PC FUN_00753650 order, 0x00753650..0x0075368c. Each component
    // keeps both products in x87 until FSUBP, then performs one f64 store.
    asm volatile(
        "fldl %[rz]\n\t"
        "fmull %[ly]\n\t"
        "fldl %[lz]\n\t"
        "fmull %[ry]\n\t"
        "fsubp %%st, %%st(1)\n\t"
        "fstpl %[ox]\n\t"

        "fldl %[lz]\n\t"
        "fmull %[rx]\n\t"
        "fldl %[rz]\n\t"
        "fmull %[lx]\n\t"
        "fsubp %%st, %%st(1)\n\t"
        "fstpl %[oy]\n\t"

        "fldl %[ry]\n\t"
        "fmull %[lx]\n\t"
        "fldl %[rx]\n\t"
        "fmull %[ly]\n\t"
        "fsubp %%st, %%st(1)\n\t"
        "fstpl %[oz]\n\t"
        : [ox] "=m"(output[0]),
          [oy] "=m"(output[1]),
          [oz] "=m"(output[2])
        : [lx] "m"(left[0]),
          [ly] "m"(left[1]),
          [lz] "m"(left[2]),
          [rx] "m"(right[0]),
          [ry] "m"(right[1]),
          [rz] "m"(right[2]));
    return output;
}

#else

inline BodyAccumulatorVector3d fun_00753650_pc_x87_cross(
    const BodyAccumulatorVector3d&,
    const BodyAccumulatorVector3d&) {
    throw std::runtime_error(
        "FUN_00753650 PC x87 cross requires an x86/x86_64 host");
}

#endif

}  // namespace detail

// PC retail FUN_00766510, source lines 759689..759695 / machine block
// 0x00766fd6..0x00767046:
//   local_1a0 = FUN_00753650(local_108, local_120)
//   HDVehicle+0x40a0/+0x40a8/+0x40b0 += local_1a0
//   local_c0/local_b8/local_b0 += local_78/local_70/local_68
//
// Phase743 deliberately starts after Phase742's BODY application. It does not
// infer producers for local_108 or the incoming local auxiliary accumulator.
inline Fun00766510PrimaryResponsePostApplicationResult
execute_fun_00766510_primary_response_post_application(
    const Fun00766510PrimaryResponsePostApplicationInput& input) {
    detail::require_fun_00766510_post_finite(
        input.caller_reference_vector,
        "FUN_00766510 caller reference vector");
    detail::require_fun_00766510_post_finite(
        input.transformed_response,
        "FUN_00766510 transformed response");
    detail::require_fun_00766510_post_finite(
        input.caller_cross_accumulator,
        "FUN_00766510 caller cross accumulator");
    detail::require_fun_00766510_post_finite(
        input.auxiliary_response,
        "FUN_00766510 auxiliary response");
    detail::require_fun_00766510_post_finite(
        input.auxiliary_accumulator,
        "FUN_00766510 auxiliary accumulator");

    Fun00766510PrimaryResponsePostApplicationResult result{};
    result.caller_cross_delta = detail::fun_00753650_pc_x87_cross(
        input.caller_reference_vector,
        input.transformed_response);
    result.caller_cross_accumulator = input.caller_cross_accumulator;
    result.auxiliary_accumulator = input.auxiliary_accumulator;

    for (std::size_t component = 0u; component < 3u; ++component) {
        result.caller_cross_accumulator[component] +=
            result.caller_cross_delta[component];
        result.auxiliary_accumulator[component] +=
            input.auxiliary_response[component];
    }

    detail::require_fun_00766510_post_finite(
        result.caller_cross_delta,
        "FUN_00766510 caller cross delta");
    detail::require_fun_00766510_post_finite(
        result.caller_cross_accumulator,
        "FUN_00766510 output caller cross accumulator");
    detail::require_fun_00766510_post_finite(
        result.auxiliary_accumulator,
        "FUN_00766510 output auxiliary accumulator");
    return result;
}

}  // namespace shift::runtime::physics
