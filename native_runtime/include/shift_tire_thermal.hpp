#pragma once

#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeTireThermalFormat =
    "SHIFT.NativeTireThermal/1";
inline constexpr const char* kTireThermalFunction = "FUN_00760b50";
inline constexpr const char* kTireThermalCallerFunction = "FUN_00770e80";

inline constexpr std::size_t kTireThermalWheelStride = 0xA80u;
inline constexpr std::size_t kTireThermalSpinMeasureOffset = 0x350u;
inline constexpr std::size_t kTireThermalSpinHeatScaleOffset = 0x858u;
inline constexpr std::size_t kTireThermalFailureGainStateOffset = 0x868u;
inline constexpr std::size_t kTireThermalFailureGainBaseOffset = 0x870u;
inline constexpr std::size_t kTireThermalToleranceOffset = 0x878u;
inline constexpr std::size_t kTireThermalTemperatureOffset = 0x888u;
inline constexpr std::size_t kTireThermalReferenceTemperatureOffset = 0x890u;
inline constexpr std::size_t kTireThermalAccumulatedHeatScaleOffset = 0x898u;
inline constexpr std::size_t kTireThermalSpeedTransferBaseOffset = 0x8A0u;
inline constexpr std::size_t kTireThermalSpeedTransferRateOffset = 0x8A8u;
inline constexpr std::size_t kTireThermalReserveOffset = 0x8B0u;
inline constexpr std::size_t kTireThermalReserveGainLaterOffset = 0x8B8u;
inline constexpr std::size_t kTireThermalReserveDepletionCapacityOffset = 0x8C0u;
inline constexpr std::size_t kTireThermalReserveFloorOffset = 0x8C8u;

inline constexpr double kTireThermalKelvinBias = 273.16;
inline constexpr double kTireThermalFailureRandomWeight = 0.25;
inline constexpr double kTireThermalFailureRandomBase = 0.75;

struct TireThermalStepInput {
    double dt = 0.0;
    double spin_measure = 0.0;
    double spin_heat_scale = 0.0;
    double accumulated_heat_scale = 0.0;
    double speed_transfer_base = 0.0;
    double speed_transfer_rate = 0.0;
    double longitudinal_velocity = 0.0;
    double ambient_temperature_a = 0.0;
    double ambient_temperature_b = 0.0;
    double temperature_state = 0.0;
    double reference_temperature = 0.0;
    double thermal_reserve = 0.0;
    double reserve_depletion_capacity = 0.0;
    double reserve_floor = 0.0;
    double thermal_tolerance = 0.0;
    double failure_gain_before = 0.0;
    double failure_gain_base = 0.0;
    double overheat_scale = 0.0;
    double failure_rng_sample = 0.0;
};

struct TireThermalStepResult {
    double source_heat = 0.0;
    double abs_longitudinal = 0.0;
    double ambient_kelvin = 0.0;
    double convective_term = 0.0;
    double net_heat = 0.0;
    double rate = 0.0;
    double temperature_before = 0.0;
    double temperature_after = 0.0;
    double thermal_reserve_before = 0.0;
    double thermal_reserve_after = 0.0;
    bool thermal_reserve_written = false;
    double failure_gain_before = 0.0;
    double failure_gain_after = 0.0;
    bool failure_gain_written = false;
};

TireThermalStepResult execute_fun_00760b50_thermal_step(
    const TireThermalStepInput& input);

}  // namespace shift::runtime::physics
