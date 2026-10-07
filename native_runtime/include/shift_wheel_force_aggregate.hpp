#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelForceAggregateFormat =
    "SHIFT.NativeWheelForceAggregate/1";
inline constexpr const char* kWheelForceAggregateFunction = "FUN_00759c90";
inline constexpr std::size_t kWheelForceAggregateRecordCount = 3u;

// PC retail record geometry. Ghidra renders the loop increment as
// `double* += 0x150`; the corresponding byte stride is 0x150 * 8 = 0xa80.
inline constexpr std::size_t kFun00759c90FirstRecordOffset = 0x7f0u;
inline constexpr std::size_t kFun00759c90RecordStrideBytes = 0xa80u;
inline constexpr std::ptrdiff_t kFun00759c90ScalarMinus8Offset = -0x08;
inline constexpr std::size_t kFun00759c90ScalarBaseOffset = 0x00u;
inline constexpr std::size_t kFun00759c90VectorBOffset = 0x98u;
inline constexpr std::size_t kFun00759c90VectorAOffset = 0xb0u;
inline constexpr std::size_t kFun00759c90PointOffset = 0xf8u;

using WheelForceAggregateVector3d = std::array<double, 3>;

struct WheelForceAggregateRecord {
    double scalar_at_base = 0.0;
    WheelForceAggregateVector3d vector_a{};
    double scalar_at_minus_8 = 0.0;
    WheelForceAggregateVector3d vector_b{};
    WheelForceAggregateVector3d point{};
};

struct WheelForceAggregateResult {
    WheelForceAggregateVector3d total{};
    WheelForceAggregateVector3d cross_total{};
    WheelForceAggregateVector3d transformed_total{};
    double scalar_output = 0.0;
};

// Caller-visible first output of FUN_00759c90. The retail function always
// computes both output vectors, but FUN_007675f0 only consumes X/Z from this
// weighted-vector total before its strict distance/speed gate.
WheelForceAggregateVector3d execute_fun_00759c90_weighted_total(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records);

WheelForceAggregateResult execute_fun_00759c90_wheel_force_aggregate(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position,
    const ConstraintRefreshFrame3f& body_frame,
    double body_field_0x120);

}  // namespace shift::runtime::physics
