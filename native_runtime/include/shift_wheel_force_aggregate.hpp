#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelForceAggregateFormat =
    "SHIFT.NativeWheelForceAggregate/1";
inline constexpr const char* kWheelForceAggregateFunction = "FUN_00759c90";
inline constexpr std::size_t kWheelForceAggregateRecordCount = 3u;
inline constexpr std::size_t kWheelForceAggregateRecordBaseOffset = 0x7f0u;
// PC machine code advances ESI by 0xa80 bytes. The decompiler renders this as
// +0x150 because its cursor is typed as double* (0x150 * 8 == 0xa80).
inline constexpr std::size_t kWheelForceAggregateRecordStride = 0xa80u;
inline constexpr std::size_t kWheelForceAggregateScalarMinus8Offset = 0x08u;
inline constexpr std::size_t kWheelForceAggregateScalarBaseOffset = 0x00u;
inline constexpr std::size_t kWheelForceAggregateVectorBOffset = 0x98u;
inline constexpr std::size_t kWheelForceAggregateVectorAOffset = 0xb0u;
inline constexpr std::size_t kWheelForceAggregatePointOffset = 0xf8u;

using WheelForceAggregateVector3d = std::array<double, 3>;

struct WheelForceAggregateRecord {
    double scalar_at_base = 0.0;
    WheelForceAggregateVector3d vector_a{};
    double scalar_at_minus_8 = 0.0;
    WheelForceAggregateVector3d vector_b{};
    WheelForceAggregateVector3d point{};
};

// Exact pair written by retail FUN_00759c90 to its two output vectors.
struct WheelForceAggregateVectorOutputs {
    WheelForceAggregateVector3d total{};
    WheelForceAggregateVector3d cross_total{};
};

struct WheelForceAggregateResult {
    WheelForceAggregateVector3d total{};
    WheelForceAggregateVector3d cross_total{};
    // Historical Phase 660 convenience outputs retained for compatibility.
    // FUN_007675f0 Phase 736 consumes only the exact retail pair above.
    WheelForceAggregateVector3d transformed_total{};
    double scalar_output = 0.0;
};

WheelForceAggregateVectorOutputs execute_fun_00759c90_vector_outputs(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position);

WheelForceAggregateResult execute_fun_00759c90_wheel_force_aggregate(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position,
    const ConstraintRefreshFrame3f& body_frame,
    double body_field_0x120);

}  // namespace shift::runtime::physics
