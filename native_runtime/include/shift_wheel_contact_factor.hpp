#pragma once

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelContactFactorFormat =
    "SHIFT.NativeWheelContactFactor/1";
inline constexpr const char* kWheelContactFactorFunction = "FUN_00758ad0";
inline constexpr const char* kWheelContactFactorCallerFunction = "FUN_00765c40";

inline constexpr std::size_t kWheelContactFactorThresholdGlobalOffset = 0xc10f94u;
inline constexpr std::size_t kWheelContactPreviousValueBase = 0x0a70u;
inline constexpr std::size_t kWheelContactFactorValueBase = 0x0a78u;
inline constexpr std::size_t kWheelContactFactorStride = 0x0150u;
inline constexpr std::size_t kWheelContactFactorCount = 4u;

inline constexpr double kWheelContactFactorHalfScale = 0.5;
inline constexpr double kWheelContactFactorAngleLimit = 6.0;
inline constexpr double kWheelContactFactorPiNumerator = 3.1415927410125732;
inline constexpr double kWheelContactFactorPiDenominator = 6.0;
inline constexpr double kWheelContactFactorCosScale = 0.02500000037252903;
inline constexpr double kWheelContactFactorCosBias = 0.9750000238418579;

struct WheelContactFactorResult {
    std::size_t wheel_index = 0u;
    double projected_value = 0.0;
    double pre_clamp = 0.0;
    double clamped_value = 0.0;
    double angle_radians = 0.0;
    double cosine = 1.0;
    double factor = 1.0;
    double previous_value = 0.0;
    std::size_t wheel_factor_offset = kWheelContactFactorValueBase;
    std::size_t previous_value_offset = kWheelContactPreviousValueBase;
};

WheelContactFactorResult execute_fun_00758ad0_contact_factor(
    double projected_value,
    double threshold_value);

std::array<WheelContactFactorResult, kWheelContactFactorCount>
execute_fun_00765c40_four_wheel_factor_storage(
    const std::array<double, kWheelContactFactorCount>& projected_values,
    double threshold_value,
    bool enabled,
    bool frame_equal,
    double frame_reference);

}  // namespace shift::runtime::physics
