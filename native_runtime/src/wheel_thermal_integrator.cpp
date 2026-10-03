#include "shift_wheel_thermal_integrator.hpp"

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

double checked_add(double a, double b, const char* label) {
    const double value = a + b;
    require_finite(value, label);
    return value;
}

double checked_mul(double a, double b, const char* label) {
    const double value = a * b;
    require_finite(value, label);
    return value;
}

}  // namespace

double compute_fun_00755a60_source_heat(
    double spin_measure,
    double spin_activity_scale,
    double activity) {

    require_finite(spin_measure, "FUN_00755a60 spin measure");
    require_finite(spin_activity_scale, "FUN_00755a60 spin activity scale");
    require_finite(activity, "FUN_00755a60 activity");
    if (activity <= 0.0) {
        return 0.0;
    }

    const double magnitude = std::abs(spin_measure);
    require_finite(magnitude, "FUN_00755a60 spin magnitude");
    const double scaled = checked_mul(
        magnitude,
        spin_activity_scale,
        "FUN_00755a60 source heat stage 1");
    return checked_mul(
        scaled,
        activity,
        "FUN_00755a60 source heat stage 2");
}

double compute_fun_00755a60_shape_factor(double factor_control) {
    require_finite(factor_control, "FUN_00755a60 factor control");

    double factor = 1.0;
    if (factor_control <= 1.0) {
        if (factor_control < 0.0) {
            throw std::invalid_argument(
                "FUN_00755a60 factor control selects sqrt of a negative value");
        }
        factor = std::sqrt(factor_control);
        require_finite(factor, "FUN_00755a60 sqrt factor");
        if (factor < 0.5) {
            factor = checked_add(
                checked_mul(
                    factor,
                    factor,
                    "FUN_00755a60 factor square"),
                0.25,
                "FUN_00755a60 factor floor adjustment");
        }
    }

    const double result = 1.0 - factor;
    require_finite(result, "FUN_00755a60 shape factor");
    return result;
}

std::array<double, 3> compute_fun_00755a60_temperature_fractions(
    double steering_a,
    double steering_b,
    double dt) {

    require_finite(steering_a, "FUN_00755a60 steering A");
    require_finite(steering_b, "FUN_00755a60 steering B");
    require_finite(dt, "FUN_00755a60 dt");

    const double half_b = checked_mul(
        steering_b,
        0.5,
        "FUN_00755a60 half steering B");
    const double f0_numerator = checked_add(
        checked_add(half_b, -steering_a, "FUN_00755a60 fraction 0 steering"),
        1.5,
        "FUN_00755a60 fraction 0 bias");
    const double f1_numerator = 1.5 - steering_b;
    require_finite(f1_numerator, "FUN_00755a60 fraction 1 numerator");
    const double f2_numerator = checked_add(
        checked_add(steering_a, half_b, "FUN_00755a60 fraction 2 steering"),
        1.5,
        "FUN_00755a60 fraction 2 bias");

    std::array<double, 3> fractions{};
    fractions[0] = checked_mul(
        f0_numerator / 3.0,
        dt,
        "FUN_00755a60 fraction 0");
    fractions[1] = checked_mul(
        f1_numerator / 3.0,
        dt,
        "FUN_00755a60 fraction 1");
    fractions[2] = checked_mul(
        f2_numerator / 3.0,
        dt,
        "FUN_00755a60 fraction 2");
    return fractions;
}

WheelThermalCoreResult execute_fun_00755a60_three_node_core(
    const WheelThermalCoreInput& input) {

    for (std::size_t index = 0; index < input.temperatures.size(); ++index) {
        require_finite(
            input.temperatures[index],
            "FUN_00755a60 temperature input");
        require_finite(input.fractions[index], "FUN_00755a60 fraction input");
    }
    require_finite(input.reservoir, "FUN_00755a60 reservoir");
    require_finite(input.activity, "FUN_00755a60 activity");
    require_finite(input.source_heat, "FUN_00755a60 source heat");
    require_finite(input.secondary_source, "FUN_00755a60 secondary source");
    require_finite(input.ambient_a_kelvin, "FUN_00755a60 ambient A Kelvin");
    require_finite(input.ambient_b_kelvin, "FUN_00755a60 ambient B Kelvin");
    require_finite(input.ambient_exchange, "FUN_00755a60 ambient exchange");
    require_finite(input.reservoir_exchange, "FUN_00755a60 reservoir exchange");

    WheelThermalCoreResult result{};
    result.reservoir_before = input.reservoir;
    double reservoir = input.reservoir;

    for (std::size_t index = 0; index < input.temperatures.size(); ++index) {
        const double original = input.temperatures[index];
        const double fraction = input.fractions[index];

        double value = checked_add(
            original,
            checked_mul(
                fraction,
                input.source_heat,
                "FUN_00755a60 node source contribution"),
            "FUN_00755a60 node after source");
        value = checked_add(
            value,
            checked_mul(
                fraction,
                input.secondary_source,
                "FUN_00755a60 node secondary contribution"),
            "FUN_00755a60 node after secondary source");

        if (input.activity > 0.0) {
            const double ambient_a_delta = input.ambient_a_kelvin - original;
            require_finite(
                ambient_a_delta,
                "FUN_00755a60 ambient A temperature delta");
            const double ambient_a_term = checked_mul(
                checked_mul(
                    fraction,
                    input.ambient_exchange,
                    "FUN_00755a60 ambient A scale"),
                ambient_a_delta,
                "FUN_00755a60 ambient A contribution");
            value = checked_add(
                value,
                ambient_a_term,
                "FUN_00755a60 node after ambient A");
        }

        const double reservoir_delta = reservoir - original;
        require_finite(
            reservoir_delta,
            "FUN_00755a60 reservoir temperature delta");
        const double transfer = checked_mul(
            reservoir_delta,
            input.reservoir_exchange,
            "FUN_00755a60 reservoir transfer");

        const double ambient_b_delta = input.ambient_b_kelvin - original;
        require_finite(
            ambient_b_delta,
            "FUN_00755a60 ambient B temperature delta");
        const double ambient_b_term = checked_mul(
            ambient_b_delta,
            input.ambient_exchange,
            "FUN_00755a60 ambient B contribution");
        value = checked_add(
            value,
            ambient_b_term,
            "FUN_00755a60 node after ambient B");
        value = checked_add(
            value,
            transfer,
            "FUN_00755a60 node after reservoir transfer");

        reservoir -= transfer;
        require_finite(reservoir, "FUN_00755a60 sequential reservoir state");
        result.temperatures_after[index] = value;
    }

    result.reservoir_after_unclamped = reservoir;
    result.reservoir_after = std::min(
        kWheelThermalReservoirHigh,
        std::max(kWheelThermalReservoirLow, reservoir));
    require_finite(result.reservoir_after, "FUN_00755a60 clamped reservoir");
    return result;
}

}  // namespace shift::runtime::physics
