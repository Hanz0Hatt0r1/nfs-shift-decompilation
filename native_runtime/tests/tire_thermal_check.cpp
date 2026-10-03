#include "shift_tire_thermal.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require_true(bool condition, const char* label) {
    if (!condition) {
        throw std::runtime_error(label);
    }
}

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

shift::runtime::physics::TireThermalStepInput low_reserve_input() {
    using namespace shift::runtime::physics;
    TireThermalStepInput input{};
    input.dt = 0.1;
    input.spin_measure = 10.0;
    input.spin_heat_scale = 2.0;
    input.accumulated_heat_scale = 3.0;
    input.speed_transfer_base = 1.0;
    input.speed_transfer_rate = 0.5;
    input.longitudinal_velocity = -4.0;
    input.ambient_temperature_a = 20.0;
    input.ambient_temperature_b = 30.0;
    input.temperature_state = 290.0;
    input.reference_temperature = 300.0;
    input.thermal_reserve = 5.0;
    input.reserve_depletion_capacity = 2.0;
    input.reserve_floor = 10.0;
    input.thermal_tolerance = 2.0;
    input.failure_gain_before = 7.0;
    input.failure_gain_base = 4.0;
    input.overheat_scale = 1.0;
    input.failure_rng_sample = 0.25;
    return input;
}

shift::runtime::physics::TireThermalStepInput high_reserve_input() {
    using namespace shift::runtime::physics;
    TireThermalStepInput input{};
    input.dt = 0.01;
    input.spin_measure = 1.0;
    input.spin_heat_scale = 1.0;
    input.accumulated_heat_scale = 1.0;
    input.speed_transfer_base = 0.0;
    input.speed_transfer_rate = 0.0;
    input.longitudinal_velocity = 0.0;
    input.ambient_temperature_a = 20.0;
    input.ambient_temperature_b = 20.0;
    input.temperature_state = 1.0;
    input.reference_temperature = 1.0;
    input.thermal_reserve = 100.0;
    input.reserve_depletion_capacity = 1.0;
    input.reserve_floor = 10.0;
    input.thermal_tolerance = 2.0;
    input.failure_gain_before = 3.0;
    input.failure_gain_base = 8.0;
    input.overheat_scale = 0.5;
    input.failure_rng_sample = 1.0;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        require_true(kTireThermalWheelStride == 0xA80u, "wheel stride mismatch");
        require_true(
            kTireThermalTemperatureOffset == 0x888u,
            "temperature offset mismatch");
        require_true(
            kTireThermalReserveOffset == 0x8B0u,
            "reserve offset mismatch");
        require_true(
            kTireThermalReserveFloorOffset == 0x8C8u,
            "reserve floor offset mismatch");

        const auto low = execute_fun_00760b50_thermal_step(low_reserve_input());
        require_close(low.source_heat, 60.0, 0.0, "low reserve source heat", max_error);
        require_close(
            low.abs_longitudinal,
            4.0,
            0.0,
            "low reserve longitudinal magnitude",
            max_error);
        require_close(
            low.ambient_kelvin,
            298.16,
            1.0e-12,
            "low reserve ambient Kelvin",
            max_error);
        require_close(
            low.convective_term,
            24.48,
            1.0e-12,
            "low reserve convective term",
            max_error);
        require_close(low.net_heat, 84.48, 1.0e-12, "low reserve net heat", max_error);
        require_close(low.rate, 8.448, 1.0e-12, "low reserve rate", max_error);
        require_close(
            low.temperature_after,
            290.8448,
            1.0e-12,
            "low reserve temperature",
            max_error);
        require_close(
            low.thermal_reserve_after,
            5.0,
            0.0,
            "low reserve preservation",
            max_error);
        require_close(
            low.failure_gain_after,
            7.0,
            0.0,
            "low reserve failure gain preservation",
            max_error);
        require_true(
            !low.thermal_reserve_written && !low.failure_gain_written,
            "low reserve path invented persistent writes");

        const auto high = execute_fun_00760b50_thermal_step(high_reserve_input());
        require_close(
            high.thermal_reserve_after,
            99.995,
            1.0e-12,
            "high reserve depletion",
            max_error);
        require_close(
            high.failure_gain_after,
            8.0,
            0.0,
            "high reserve random blend",
            max_error);
        require_true(
            high.thermal_reserve_written && high.failure_gain_written,
            "high reserve writes were not reported");
        require_true(high.temperature_after != 1.0, "high reserve temperature did not advance");

        auto outside_tolerance = high_reserve_input();
        outside_tolerance.temperature_state = 5.0;
        outside_tolerance.reference_temperature = 1.0;
        const auto outside = execute_fun_00760b50_thermal_step(outside_tolerance);
        require_close(
            outside.failure_gain_after,
            4.0,
            0.0,
            "outside-tolerance failure gain",
            max_error);

        auto exhausted_input = high_reserve_input();
        exhausted_input.dt = 1.0;
        exhausted_input.spin_measure = 100.0;
        exhausted_input.spin_heat_scale = 100.0;
        exhausted_input.accumulated_heat_scale = 100.0;
        exhausted_input.temperature_state = 300.0;
        exhausted_input.reference_temperature = 250.0;
        exhausted_input.thermal_reserve = 11.0;
        exhausted_input.reserve_depletion_capacity = 100.0;
        exhausted_input.reserve_floor = 10.0;
        exhausted_input.overheat_scale = 1.0;
        const auto exhausted =
            execute_fun_00760b50_thermal_step(exhausted_input);
        require_close(
            exhausted.thermal_reserve_after,
            0.0,
            0.0,
            "exhausted reserve zero",
            max_error);
        require_close(
            exhausted.failure_gain_after,
            0.0,
            0.0,
            "exhausted failure gain zero",
            max_error);
        require_close(exhausted.rate, 0.0, 0.0, "exhausted rate zero", max_error);
        require_close(
            exhausted.temperature_after,
            300.0,
            0.0,
            "exhausted temperature preservation",
            max_error);
        require_true(
            exhausted.thermal_reserve_written && exhausted.failure_gain_written,
            "exhaustion writes were not reported");

        bool zero_divisor_rejected = false;
        try {
            auto invalid = low_reserve_input();
            invalid.thermal_reserve = 0.0;
            invalid.reserve_floor = 0.0;
            (void)execute_fun_00760b50_thermal_step(invalid);
        } catch (const std::invalid_argument&) {
            zero_divisor_rejected = true;
        }
        require_true(zero_divisor_rejected, "zero reserve divisor was accepted");

        bool non_finite_rejected = false;
        try {
            auto invalid = low_reserve_input();
            invalid.temperature_state = std::numeric_limits<double>::infinity();
            (void)execute_fun_00760b50_thermal_step(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require_true(non_finite_rejected, "non-finite input was accepted");

        bool overflow_rejected = false;
        try {
            auto invalid = low_reserve_input();
            invalid.spin_measure = std::numeric_limits<double>::max();
            invalid.spin_heat_scale = 2.0;
            (void)execute_fun_00760b50_thermal_step(invalid);
        } catch (const std::invalid_argument&) {
            overflow_rejected = true;
        }
        require_true(overflow_rejected, "non-finite intermediate was accepted");

        std::cout
            << "{\"format\":\"" << kNativeTireThermalFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"" << kTireThermalFunction << "\","
            << "\"caller\":\"" << kTireThermalCallerFunction << "\","
            << "\"wheel_stride\":" << kTireThermalWheelStride << ','
            << "\"floor_normalization_proven\":true,"
            << "\"cubic_reserve_depletion_proven\":true,"
            << "\"failure_gain_branch_proven\":true,"
            << "\"reserve_exhaustion_zero_path_proven\":true,"
            << "\"persistent_write_mask_proven\":true,"
            << "\"longitudinal_transform_external\":true,"
            << "\"overheat_scale_external\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
