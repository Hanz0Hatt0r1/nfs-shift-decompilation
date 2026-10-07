#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelForceAggregateFormat =
    "SHIFT.NativeWheelForceAggregate/1";
inline constexpr const char* kFun00759c90AggregateFormat =
    "SHIFT.Fun00759c90Aggregate/1";
inline constexpr const char* kWheelForceAggregateFunction = "FUN_00759c90";
inline constexpr std::size_t kWheelForceAggregateRecordCount = 3u;

// Exact PC retail byte geometry. The decompiler's `pdVar3 += 0x150` is
// double-pointer arithmetic, so the machine-code stride is 0x150 * 8 = 0xa80.
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

// Exact output contract of PC retail FUN_00759c90: two three-lane f64 vectors.
struct Fun00759c90AggregateResult {
    WheelForceAggregateVector3d total{};
    WheelForceAggregateVector3d cross_total{};
};

// Earlier production boundary. The record producer/freshness remains external;
// FUN_007675f0 no longer accepts its already-derived projected scalar.
struct Fun00759c90RecordBoundary {
    std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount> records{};
    bool ready = false;
};

Fun00759c90AggregateResult execute_fun_00759c90_three_record_aggregate(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position);

// Historical Phase 660 compatibility result. PC retail FUN_00759c90 itself ends
// after total/cross_total. transformed_total/scalar_output reproduce the older
// composite wrapper, whose transform/divide tail corresponds to adjacent
// FUN_00759bb0-style arithmetic rather than FUN_00759c90's return contract.
struct WheelForceAggregateResult {
    WheelForceAggregateVector3d total{};
    WheelForceAggregateVector3d cross_total{};
    WheelForceAggregateVector3d transformed_total{};
    double scalar_output = 0.0;
};

WheelForceAggregateResult execute_fun_00759c90_wheel_force_aggregate(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position,
    const ConstraintRefreshFrame3f& body_frame,
    double body_field_0x120);

}  // namespace shift::runtime::physics
