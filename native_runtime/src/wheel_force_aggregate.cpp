#include "shift_wheel_force_aggregate.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

WheelForceAggregateVector3d cross(
    const WheelForceAggregateVector3d& left,
    const WheelForceAggregateVector3d& right) {

    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

}  // namespace

Fun00759c90AggregateResult execute_fun_00759c90_three_record_aggregate(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position) {

    require_finite(body_position, "FUN_00759c90 BODY position");

    Fun00759c90AggregateResult result{};
    for (const auto& record : records) {
        require_finite_value(record.scalar_at_base, "FUN_00759c90 record scalar +0x00");
        require_finite(record.vector_a, "FUN_00759c90 record vector +0xb0");
        require_finite_value(record.scalar_at_minus_8, "FUN_00759c90 record scalar -0x08");
        require_finite(record.vector_b, "FUN_00759c90 record vector +0x98");
        require_finite(record.point, "FUN_00759c90 record point +0xf8");

        WheelForceAggregateVector3d summed{};
        WheelForceAggregateVector3d relative{};
        for (std::size_t component = 0; component < 3u; ++component) {
            summed[component] =
                record.vector_a[component] * record.scalar_at_base +
                record.vector_b[component] * record.scalar_at_minus_8;
            relative[component] = record.point[component] - body_position[component];
            result.total[component] += summed[component];
        }
        const auto cross_value = cross(relative, summed);
        for (std::size_t component = 0; component < 3u; ++component) {
            result.cross_total[component] += cross_value[component];
        }
    }

    require_finite(result.total, "FUN_00759c90 total vector");
    require_finite(result.cross_total, "FUN_00759c90 cross total");
    return result;
}

WheelForceAggregateResult execute_fun_00759c90_wheel_force_aggregate(
    const std::array<WheelForceAggregateRecord, kWheelForceAggregateRecordCount>& records,
    const WheelForceAggregateVector3d& body_position,
    const ConstraintRefreshFrame3f& body_frame,
    double body_field_0x120) {

    // Preserve the Phase 660 public wrapper for old fixtures while making the
    // exact retail FUN_00759c90 output boundary explicit above.
    require_finite(body_frame, "legacy FUN_00759c90 composite BODY frame");
    require_finite_value(body_field_0x120, "legacy FUN_00759c90 composite BODY +0x120");
    if (body_field_0x120 == 0.0) {
        throw std::invalid_argument(
            "legacy FUN_00759c90 composite BODY +0x120 must be non-zero");
    }

    const auto exact = execute_fun_00759c90_three_record_aggregate(
        records,
        body_position);

    WheelForceAggregateResult result{};
    result.total = exact.total;
    result.cross_total = exact.cross_total;
    result.transformed_total =
        transform_fun_007af0a0_refresh(body_frame, result.total);
    result.scalar_output = result.transformed_total[0] / body_field_0x120;
    require_finite_value(
        result.scalar_output,
        "legacy FUN_00759c90 composite scalar output");
    return result;
}

}  // namespace shift::runtime::physics
