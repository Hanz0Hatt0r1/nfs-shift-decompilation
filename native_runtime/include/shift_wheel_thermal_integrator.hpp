#pragma once

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelThermalIntegratorFormat =
    "SHIFT.NativeWheelThermalIntegrator/1";
inline constexpr const char* kWheelThermalIntegratorFunction = "FUN_00755a60";
inline constexpr const char* kWheelThermalIntegratorCaller = "FUN_00770e80";

inline constexpr std::size_t kWheelThermalCount = 4u;
inline constexpr std::size_t kWheelThermalBaseOffset = 0x400u;
inline constexpr std::size_t kWheelThermalStrideBytes = 0xa80u;
inline constexpr std::size_t kWheelThermalStrideDoubles = 0x150u;

inline constexpr std::size_t kWheelThermalTemperature0Offset = 0x7b0u;
inline constexpr std::size_t kWheelThermalTemperature1Offset = 0x7b8u;
inline constexpr std::size_t kWheelThermalTemperature2Offset = 0x7c0u;
inline constexpr std::size_t kWheelThermalReservoirOffset = 0x7c8u;
inline constexpr std::size_t kWheelThermalDerivedReservoirOffset = 0x7d8u;
inline constexpr std::size_t kWheelThermalWearOffset = 0x7f8u;
inline constexpr std::size_t kWheelThermalOutputOffset = 0x800u;
inline constexpr std::size_t kWheelThermalAccumulatorOffset = 0x850u;

inline constexpr double kWheelThermalKelvinBias = 273.16;
inline constexpr double kWheelThermalReservoirLow = 273.16;
inline constexpr double kWheelThermalReservoirHigh = 546.32;
inline constexpr double kWheelThermalWearFloor = 0.6875;

using WheelThermalVector3d = std::array<double, 3>;

struct WheelThermalInputs {
    double dt = 0.0;
    double ambient_a = 0.0;
    double ambient_b = 0.0;
    double spin_measure = 0.0;
    double spin_activity_scale = 0.0;
    double activity = 0.0;
    double factor_control = 0.0;
    double heat_shape = 0.0;
    double heat_gain = 0.0;
    double steering_a_product = 0.0;
    double steering_b_product = 0.0;
    double steering_b_base = 0.0;
    double steering_b_reference = 0.0;
    double steering_b_gain = 0.0;
    double sqrt_input_base = 0.0;
    double global_constant_c12c24 = 0.0;
    double ambient_coupling_a = 0.0;
    double ambient_coupling_b = 0.0;
    double reservoir_temperature = 0.0;
    WheelThermalVector3d temperatures{};
    double reservoir_exchange = 0.0;
    double temp_reference = 0.0;
    double temp_gain_negative = 0.0;
    double temp_gain_positive = 0.0;
    double temp_alert_threshold = 0.0;
    double abrasion_scale = 0.0;
    double abrasion_accumulator = 0.0;
    double wear_state = 0.0;
    double derived_reservoir_scale = 0.0;
    double derived_aux_scale = 0.0;
    double derived_aux_bias = 0.0;
    double output_limit_reference = 0.0;
    bool wear_enabled = false;
    double global_wear_scale = 0.0;
    double average_temperature_scale = 1.0;
};

struct WheelThermalStep {
    double source_heat = 0.0;
    double shape_factor = 0.0;
    double secondary_source = 0.0;
    double steering_a = 0.0;
    double steering_b = 0.0;
    WheelThermalVector3d fractions{};
    WheelThermalVector3d temperatures_after{};
    double reservoir_before = 0.0;
    double reservoir_after = 0.0;
    double average_temperature = 0.0;
    double abrasion_term = 0.0;
    double wear_after = 0.0;
    double normalized_temperature_delta = 0.0;
    double limited_temperature_factor = 0.0;
    double output = 0.0;
    double derived_reservoir_field = 0.0;
    double derived_auxiliary_field = 0.0;
    bool wear_floor_crossed = false;
    bool overtemperature_condition = false;
};

double compute_fun_00755a60_source_heat(
    double spin_measure,
    double spin_activity_scale,
    double activity);

double compute_fun_00755a60_shape_factor(double factor_control);

WheelThermalVector3d compute_fun_00755a60_temperature_fractions(
    double steering_a,
    double steering_b,
    double dt);

WheelThermalStep execute_fun_00755a60_thermal_integrator(
    const WheelThermalInputs& input);

}  // namespace shift::runtime::physics
