#include "shift_wheel_thermal_integrator.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

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

shift::runtime::physics::WheelThermalInputs base_input() {
    using namespace shift::runtime::physics;
    WheelThermalInputs input{};
    input.dt = 0.1;
    input.ambient_a = 20.0;
    input.ambient_b = 30.0;
    input.spin_measure = 10.0;
    input.spin_activity_scale = 2.0;
    input.activity = 0.0;
    input.factor_control = 0.0;
    input.heat_shape = 2.0;
    input.heat_gain = 1.0;
    input.steering_a_product = 0.0;
    input.steering_b_product = 0.0;
    input.steering_b_base = 300.0;
    input.steering_b_reference = 300.0;
    input.steering_b_gain = 1.0;
    input.sqrt_input_base = 0.0;
    input.global_constant_c12c24 = 0.0;
    input.ambient_coupling_a = 0.0;
    input.ambient_coupling_b = 0.0;
    input.reservoir_temperature = 300.0;
    input.temperatures = {300.0, 300.0, 300.0};
    input.reservoir_exchange = 0.0;
    input.temp_reference = 300.0;
    input.temp_gain_negative = 0.1;
    input.temp_gain_positive = 0.1;
    input.temp_alert_threshold = 350.0;
    input.abrasion_scale = 0.0;
    input.abrasion_accumulator = 0.0;
    input.wear_state = 1.0;
    input.derived_reservoir_scale = 1.0;
    input.derived_aux_scale = 1.0;
    input.derived_aux_bias = 0.0;
    input.output_limit_reference = 1.0;
    input.wear_enabled = true;
    input.global_wear_scale = 1.0;
    input.average_temperature_scale = 1.0;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        if (kWheelThermalCount != 4u ||
            kWheelThermalBaseOffset != 0x400u ||
            kWheelThermalStrideBytes != 0xa80u ||
            kWheelThermalStrideDoubles != 0x150u ||
            kWheelThermalTemperature0Offset != 0x7b0u ||
            kWheelThermalTemperature1Offset != 0x7b8u ||
            kWheelThermalTemperature2Offset != 0x7c0u ||
            kWheelThermalReservoirOffset != 0x7c8u ||
            kWheelThermalDerivedReservoirOffset != 0x7d8u ||
            kWheelThermalWearOffset != 0x7f8u ||
            kWheelThermalOutputOffset != 0x800u ||
            kWheelThermalAccumulatorOffset != 0x850u) {
            throw std::runtime_error("FUN_00755a60 layout constants mismatch");
        }

        require_close(
            compute_fun_00755a60_source_heat(10.0, 2.0, 0.0),
            0.0,
            0.0,
            "source heat zero branch",
            max_error);
        require_close(
            compute_fun_00755a60_source_heat(-10.0, 2.0, 1.5),
            30.0,
            0.0,
            "source heat active branch",
            max_error);

        require_close(
            compute_fun_00755a60_shape_factor(0.0),
            0.75,
            0.0,
            "shape factor zero",
            max_error);
        require_close(
            compute_fun_00755a60_shape_factor(0.25),
            0.5,
            0.0,
            "shape factor quarter",
            max_error);
        require_close(
            compute_fun_00755a60_shape_factor(4.0),
            0.0,
            0.0,
            "shape factor upper branch",
            max_error);

        const auto fractions =
            compute_fun_00755a60_temperature_fractions(0.0, 0.0, 0.1);
        for (const double value : fractions) {
            require_close(value, 0.05, 1e-15, "temperature fraction", max_error);
        }

        auto reservoir_input = base_input();
        reservoir_input.reservoir_temperature = 310.0;
        reservoir_input.reservoir_exchange = 1.0;
        const auto reservoir =
            execute_fun_00755a60_thermal_integrator(reservoir_input);
        const double expected_temperatures[] = {301.0, 300.9, 300.81};
        for (std::size_t index = 0; index < 3u; ++index) {
            require_close(
                reservoir.temperatures_after[index],
                expected_temperatures[index],
                1e-12,
                "sequential reservoir temperature",
                max_error);
        }
        require_close(
            reservoir.reservoir_after,
            307.29,
            1e-12,
            "sequential reservoir remainder",
            max_error);

        auto active_input = base_input();
        active_input.activity = 1.0;
        const auto active = execute_fun_00755a60_thermal_integrator(active_input);
        require_close(active.source_heat, 20.0, 0.0, "active source heat", max_error);
        require_close(active.shape_factor, 0.75, 0.0, "active shape", max_error);
        require_close(active.secondary_source, 3.0, 0.0, "secondary source", max_error);
        for (const double value : active.temperatures_after) {
            require_close(value, 301.15, 1e-12, "active temperature", max_error);
        }

        auto clamped_input = base_input();
        clamped_input.reservoir_temperature = 1000.0;
        clamped_input.derived_reservoir_scale = 2.0;
        clamped_input.derived_aux_scale = 3.0;
        clamped_input.derived_aux_bias = 4.0;
        const auto clamped = execute_fun_00755a60_thermal_integrator(clamped_input);
        require_close(
            clamped.reservoir_after,
            kWheelThermalReservoirHigh,
            0.0,
            "reservoir high clamp",
            max_error);
        require_close(
            clamped.derived_reservoir_field,
            2.0 * kWheelThermalReservoirHigh,
            1e-12,
            "derived reservoir",
            max_error);
        require_close(
            clamped.derived_auxiliary_field,
            3.0 * 2.0 * kWheelThermalReservoirHigh + 4.0,
            1e-12,
            "derived auxiliary",
            max_error);

        auto wear_input = base_input();
        wear_input.dt = 1.0;
        wear_input.abrasion_scale = 1.0;
        const auto worn = execute_fun_00755a60_thermal_integrator(wear_input);
        if (!(worn.abrasion_term > 0.0) || !worn.wear_floor_crossed) {
            throw std::runtime_error("wear-floor branch was not taken");
        }
        require_close(
            worn.wear_after,
            kWheelThermalWearFloor,
            0.0,
            "wear floor",
            max_error);

        const auto base = execute_fun_00755a60_thermal_integrator(base_input());
        require_close(
            base.normalized_temperature_delta,
            0.0,
            1e-15,
            "base normalized factor",
            max_error);
        require_close(
            base.limited_temperature_factor,
            1.0,
            0.0,
            "base limited factor",
            max_error);
        require_close(base.output, 0.5, 0.0, "base output", max_error);

        if (kWheelThermalKelvinBias != 273.16 ||
            kWheelThermalReservoirLow != 273.16 ||
            kWheelThermalReservoirHigh != 546.32 ||
            kWheelThermalWearFloor != 0.6875) {
            throw std::runtime_error("FUN_00755a60 constants mismatch");
        }

        bool negative_shape_rejected = false;
        try {
            (void)compute_fun_00755a60_shape_factor(-0.25);
        } catch (const std::invalid_argument&) {
            negative_shape_rejected = true;
        }
        if (!negative_shape_rejected) {
            throw std::runtime_error("negative sqrt input was accepted");
        }

        bool zero_normalization_rejected = false;
        try {
            auto invalid = base_input();
            invalid.steering_b_base = 0.0;
            (void)execute_fun_00755a60_thermal_integrator(invalid);
        } catch (const std::invalid_argument&) {
            zero_normalization_rejected = true;
        }
        if (!zero_normalization_rejected) {
            throw std::runtime_error("zero normalization reference was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = base_input();
            invalid.temperature_0 = 0.0;
        } catch (...) {
            // Kept empty intentionally; WheelThermalInputs has a packed triplet.
        }
        try {
            auto invalid = base_input();
            invalid.temperatures[1] = std::numeric_limits<double>::infinity();
            (void)execute_fun_00755a60_thermal_integrator(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite thermal input was accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeWheelThermalIntegratorFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00755a60\","
            << "\"caller\":\"FUN_00770e80\","
            << "\"wheel_count\":4,"
            << "\"three_node_update_proven\":true,"
            << "\"sequential_reservoir_exchange_proven\":true,"
            << "\"reservoir_clamp_proven\":true,"
            << "\"wear_floor_proven\":true,"
            << "\"final_output_proven\":true,"
            << "\"event_side_effects_proven\":false,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
