#pragma once

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelThermalCoreFormat =
    "SHIFT.NativeWheelThermalCore/1";
inline constexpr const char* kWheelThermalIntegratorFunction = "FUN_00755a60";
inline constexpr const char* kWheelThermalIntegratorCaller = "FUN_00770e80";

inline constexpr std::size_t kWheelThermalObjectBaseOffset = 0x400u;
inline constexpr std::size_t kWheelThermalSubstructureStride = 0x150u;
inline constexpr std::size_t kWheelThermalWheelCount = 4u;
inline constexpr std::size_t kWheelThermalTemperature0Offset = 0x7B0u;
inline constexpr std::size_t kWheelThermalTemperature1Offset = 0x7B8u;
inline constexpr std::size_t kWheelThermalTemperature2Offset = 0x7C0u;
inline constexpr std::size_t kWheelThermalReservoirOffset = 0x7C8u;

inline constexpr double kWheelThermalKelvinBias = 273.16;
inline constexpr double kWheelThermalReservoirLow = 273.16;
inline constexpr double kWheelThermalReservoirHigh = 546.32;

struct WheelThermalCoreInput {
    std::array<double, 3> temperatures{};
    double reservoir = 0.0;
    std::array<double, 3> fractions{};
    double activity = 0.0;
    double source_heat = 0.0;
    double secondary_source = 0.0;
    double ambient_a_kelvin = 0.0;
    double ambient_b_kelvin = 0.0;
    double ambient_exchange = 0.0;
    double reservoir_exchange = 0.0;
};

struct WheelThermalCoreResult {
    std::array<double, 3> temperatures_after{};
    double reservoir_before = 0.0;
    double reservoir_after_unclamped = 0.0;
    double reservoir_after = 0.0;
};

double compute_fun_00755a60_source_heat(
    double spin_measure,
    double spin_activity_scale,
    double activity);

double compute_fun_00755a60_shape_factor(double factor_control);

std::array<double, 3> compute_fun_00755a60_temperature_fractions(
    double steering_a,
    double steering_b,
    double dt);

WheelThermalCoreResult execute_fun_00755a60_three_node_core(
    const WheelThermalCoreInput& input);

}  // namespace shift::runtime::physics
