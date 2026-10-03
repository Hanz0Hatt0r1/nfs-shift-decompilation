#include "shift_wheel_thermal_integrator.hpp"

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

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        require_true(kWheelThermalObjectBaseOffset == 0x400u, "wheel base mismatch");
        require_true(kWheelThermalSubstructureStride == 0x150u, "wheel stride mismatch");
        require_true(kWheelThermalWheelCount == 4u, "wheel count mismatch");
        require_true(kWheelThermalTemperature0Offset == 0x7B0u, "temperature 0 offset mismatch");
        require_true(kWheelThermalReservoirOffset == 0x7C8u, "reservoir offset mismatch");

        require_close(
            compute_fun_00755a60_source_heat(10.0, 2.0, 0.0),
            0.0,
            0.0,
            "inactive source heat",
            max_error);
        require_close(
            compute_fun_00755a60_source_heat(-10.0, 2.0, 1.5),
            30.0,
            0.0,
            "active source heat",
            max_error);

        require_close(
            compute_fun_00755a60_shape_factor(0.0),
            0.75,
            0.0,
            "shape factor zero branch",
            max_error);
        require_close(
            compute_fun_00755a60_shape_factor(0.25),
            0.5,
            0.0,
            "shape factor half branch",
            max_error);
        require_close(
            compute_fun_00755a60_shape_factor(4.0),
            0.0,
            0.0,
            "shape factor bypass branch",
            max_error);

        const auto fractions = compute_fun_00755a60_temperature_fractions(0.0, 0.0, 0.1);
        for (double fraction : fractions) {
            require_close(fraction, 0.05, 1.0e-15, "temperature fraction", max_error);
        }

        WheelThermalCoreInput sequential{};
        sequential.temperatures = {300.0, 300.0, 300.0};
        sequential.reservoir = 310.0;
        sequential.fractions = fractions;
        sequential.activity = 0.0;
        sequential.source_heat = 0.0;
        sequential.secondary_source = 0.0;
        sequential.ambient_a_kelvin = 293.16;
        sequential.ambient_b_kelvin = 303.16;
        sequential.ambient_exchange = 0.0;
        sequential.reservoir_exchange = 0.1;
        const auto sequential_result = execute_fun_00755a60_three_node_core(sequential);
        require_close(sequential_result.temperatures_after[0], 301.0, 1.0e-12, "sequential node 0", max_error);
        require_close(sequential_result.temperatures_after[1], 300.9, 1.0e-12, "sequential node 1", max_error);
        require_close(sequential_result.temperatures_after[2], 300.81, 1.0e-12, "sequential node 2", max_error);
        require_close(sequential_result.reservoir_after_unclamped, 307.29, 1.0e-12, "sequential reservoir", max_error);
        require_close(sequential_result.reservoir_after, 307.29, 1.0e-12, "sequential clamped reservoir", max_error);

        WheelThermalCoreInput sources{};
        sources.temperatures = {300.0, 300.0, 300.0};
        sources.reservoir = 300.0;
        sources.fractions = fractions;
        sources.activity = 1.0;
        sources.source_heat = 20.0;
        sources.secondary_source = 3.0;
        sources.ambient_a_kelvin = 293.16;
        sources.ambient_b_kelvin = 303.16;
        sources.ambient_exchange = 0.0;
        sources.reservoir_exchange = 0.0;
        const auto source_result = execute_fun_00755a60_three_node_core(sources);
        for (double temperature : source_result.temperatures_after) {
            require_close(temperature, 301.15, 1.0e-12, "source contribution temperature", max_error);
        }

        auto high_clamp = sources;
        high_clamp.reservoir = 1000.0;
        const auto high = execute_fun_00755a60_three_node_core(high_clamp);
        require_close(high.reservoir_after, 546.32, 0.0, "reservoir high clamp", max_error);

        auto low_clamp = sources;
        low_clamp.reservoir = 100.0;
        const auto low = execute_fun_00755a60_three_node_core(low_clamp);
        require_close(low.reservoir_after, 273.16, 0.0, "reservoir low clamp", max_error);

        WheelThermalCoreInput ambient_gate{};
        ambient_gate.temperatures = {300.0, 300.0, 300.0};
        ambient_gate.reservoir = 300.0;
        ambient_gate.fractions = {0.5, 0.0, 0.0};
        ambient_gate.source_heat = 0.0;
        ambient_gate.secondary_source = 0.0;
        ambient_gate.ambient_a_kelvin = 310.0;
        ambient_gate.ambient_b_kelvin = 300.0;
        ambient_gate.ambient_exchange = 0.2;
        ambient_gate.reservoir_exchange = 0.0;
        ambient_gate.activity = 0.0;
        const auto ambient_inactive = execute_fun_00755a60_three_node_core(ambient_gate);
        require_close(ambient_inactive.temperatures_after[0], 300.0, 0.0, "inactive ambient A gate", max_error);
        ambient_gate.activity = 1.0;
        const auto ambient_active = execute_fun_00755a60_three_node_core(ambient_gate);
        require_close(ambient_active.temperatures_after[0], 301.0, 1.0e-12, "active ambient A gate", max_error);

        bool negative_sqrt_rejected = false;
        try {
            (void)compute_fun_00755a60_shape_factor(-0.25);
        } catch (const std::invalid_argument&) {
            negative_sqrt_rejected = true;
        }
        require_true(negative_sqrt_rejected, "negative sqrt input was accepted");

        bool non_finite_rejected = false;
        try {
            auto invalid = sources;
            invalid.reservoir = std::numeric_limits<double>::infinity();
            (void)execute_fun_00755a60_three_node_core(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require_true(non_finite_rejected, "non-finite thermal core input was accepted");

        bool overflow_rejected = false;
        try {
            (void)compute_fun_00755a60_source_heat(
                std::numeric_limits<double>::max(),
                2.0,
                1.0);
        } catch (const std::invalid_argument&) {
            overflow_rejected = true;
        }
        require_true(overflow_rejected, "source heat overflow was accepted");

        std::cout
            << "{\"format\":\"" << kNativeWheelThermalCoreFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"" << kWheelThermalIntegratorFunction << "\","
            << "\"caller\":\"" << kWheelThermalIntegratorCaller << "\","
            << "\"wheel_count\":" << kWheelThermalWheelCount << ','
            << "\"wheel_substructure_stride\":" << kWheelThermalSubstructureStride << ','
            << "\"source_heat_proven\":true,"
            << "\"shape_factor_proven\":true,"
            << "\"temperature_fraction_proven\":true,"
            << "\"sequential_reservoir_transfer_proven\":true,"
            << "\"reservoir_clamp_proven\":true,"
            << "\"secondary_source_producer_external\":true,"
            << "\"ambient_exchange_producer_external\":true,"
            << "\"wear_grip_tail_external\":true,"
            << "\"full_function_ported\":false,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
