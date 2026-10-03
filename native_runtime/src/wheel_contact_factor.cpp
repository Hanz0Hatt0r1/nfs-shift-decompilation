#include "shift_wheel_contact_factor.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(label) + " must be finite");
    }
}

double round_float32(double value) {
    require_finite(value, "FUN_00758ad0 pre-round factor");
    const float rounded = static_cast<float>(value);
    if (!std::isfinite(rounded)) {
        throw std::invalid_argument("FUN_00758ad0 float32 result is non-finite");
    }
    return static_cast<double>(rounded);
}

}  // namespace

WheelContactFactorResult execute_fun_00758ad0_contact_factor(
    double projected_value,
    double threshold_value) {

    require_finite(projected_value, "FUN_00758ad0 projected value");
    require_finite(threshold_value, "FUN_00758ad0 threshold value");

    WheelContactFactorResult result{};
    result.projected_value = projected_value;
    result.pre_clamp =
        std::abs(projected_value) -
        threshold_value * kWheelContactFactorHalfScale;
    result.clamped_value =
        std::clamp(
            result.pre_clamp,
            0.0,
            kWheelContactFactorAngleLimit);
    result.angle_radians =
        result.clamped_value *
        kWheelContactFactorPiNumerator /
        kWheelContactFactorPiDenominator;
    result.cosine = std::cos(result.angle_radians);
    result.factor = round_float32(
        result.cosine * kWheelContactFactorCosScale +
        kWheelContactFactorCosBias);

    require_finite(result.pre_clamp, "FUN_00758ad0 pre-clamp");
    require_finite(result.angle_radians, "FUN_00758ad0 angle");
    require_finite(result.cosine, "FUN_00758ad0 cosine");
    return result;
}

std::array<WheelContactFactorResult, kWheelContactFactorCount>
execute_fun_00765c40_four_wheel_factor_storage(
    const std::array<double, kWheelContactFactorCount>& projected_values,
    double threshold_value,
    bool enabled,
    bool frame_equal,
    double frame_reference) {

    require_finite(threshold_value, "FUN_00765c40 threshold value");
    require_finite(frame_reference, "FUN_00765c40 frame reference");

    const double previous_value = frame_equal ? frame_reference : 0.0;
    std::array<WheelContactFactorResult, kWheelContactFactorCount> result{};
    for (std::size_t wheel = 0; wheel < kWheelContactFactorCount; ++wheel) {
        require_finite(projected_values[wheel], "FUN_00765c40 projected value");

        WheelContactFactorResult row{};
        if (enabled) {
            row = execute_fun_00758ad0_contact_factor(
                projected_values[wheel],
                threshold_value);
        } else {
            row.projected_value = projected_values[wheel];
            row.cosine = 1.0;
            row.factor = 1.0;
        }

        row.wheel_index = wheel;
        row.previous_value = previous_value;
        row.wheel_factor_offset =
            kWheelContactFactorValueBase + wheel * kWheelContactFactorStride;
        row.previous_value_offset =
            kWheelContactPreviousValueBase + wheel * kWheelContactFactorStride;
        result[wheel] = row;
    }
    return result;
}

}  // namespace shift::runtime::physics
