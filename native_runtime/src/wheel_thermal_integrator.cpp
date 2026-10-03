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

template <typename Range>
void require_finite_range(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

double clamp_value(double value, double low, double high) {
    require_finite(value, "FUN_00755a60 clamp input");
    return std::min(high, std::max(low, value));
}

void require_inputs(const WheelThermalInputs& input) {
    const double values[] = {
        input.dt,
        input.ambient_a,
        input.ambient_b,
        input.spin_measure,
        input.spin_activity_scale,
        input.activity,
        input.factor_control,
        input.heat_shape,
        input.heat_gain,
        input.steering_a_product,
        input.steering_b_product,
        input.steering_b_base,
        input.steering_b_reference,
        input.steering_b_gain,
        input.sqrt_input_base,
        input.global_constant_c12c24,
        input.ambient_coupling_a,
        input.ambient_coupling_b,
        input.reservoir_temperature,
        input.reservoir_exchange,
        input.temp_reference,
        input.temp_gain_negative,
        input.temp_gain_positive,
        input.temp_alert_threshold,
        input.abrasion_scale,
        input.abrasion_accumulator,
        input.wear_state,
        input.derived_reservoir_scale,
        input.derived_aux_scale,
        input.derived_aux_bias,
        input.output_limit_reference,
        input.global_wear_scale,
        input.average_temperature_scale,
    };
    require_finite_range(values, "FUN_00755a60 scalar input");
    require_finite_range(input.temperatures, "FUN_00755a60 temperatures");
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
    const double result =
        std::abs(spin_measure) * spin_activity_scale * activity;
    require_finite(result, "FUN_00755a60 source heat");
    return result;
}

double compute_fun_00755a60_shape_factor(double factor_control) {
    require_finite(factor_control, "FUN_00755a60 factor control");
    double factor = 1.0;
    if (factor_control <= 1.0) {
        if (factor_control < 0.0) {
            throw std::invalid_argument(
                "FUN_00755a60 factor control would enter sqrt with a negative value");
        }
        factor = std::sqrt(factor_control);
        if (factor < 0.5) {
            factor = factor * factor + 0.25;
        }
    }
    const double result = 1.0 - factor;
    require_finite(result, "FUN_00755a60 shape factor");
    return result;
}

WheelThermalVector3d compute_fun_00755a60_temperature_fractions(
    double steering_a,
    double steering_b,
    double dt) {

    require_finite(steering_a, "FUN_00755a60 steering A");
    require_finite(steering_b, "FUN_00755a60 steering B");
    require_finite(dt, "FUN_00755a60 dt");
    WheelThermalVector3d result = {
        ((steering_b * 0.5 - steering_a + 1.5) / 3.0) * dt,
        ((1.5 - steering_b) / 3.0) * dt,
        ((steering_a + steering_b * 0.5 + 1.5) / 3.0) * dt,
    };
    require_finite_range(result, "FUN_00755a60 temperature fractions");
    return result;
}

WheelThermalStep execute_fun_00755a60_thermal_integrator(
    const WheelThermalInputs& input) {

    require_inputs(input);

    const double ambient_a = input.ambient_a + kWheelThermalKelvinBias;
    const double ambient_b = input.ambient_b + kWheelThermalKelvinBias;
    require_finite(ambient_a, "FUN_00755a60 ambient A Kelvin");
    require_finite(ambient_b, "FUN_00755a60 ambient B Kelvin");

    WheelThermalStep result{};
    result.source_heat = compute_fun_00755a60_source_heat(
        input.spin_measure,
        input.spin_activity_scale,
        input.activity);
    result.shape_factor =
        compute_fun_00755a60_shape_factor(input.factor_control);
    result.secondary_source =
        result.shape_factor * input.activity * input.heat_shape * input.heat_shape *
        input.heat_gain;
    require_finite(result.secondary_source, "FUN_00755a60 secondary source");

    result.steering_a = clamp_value(input.steering_a_product, -1.0, 1.0);
    const double local_steering_b =
        input.steering_b_product + input.steering_b_base;
    require_finite(local_steering_b, "FUN_00755a60 local steering B");
    result.steering_b = clamp_value(
        (local_steering_b - input.steering_b_reference) * input.steering_b_gain,
        -1.0,
        1.0);
    result.fractions = compute_fun_00755a60_temperature_fractions(
        result.steering_a,
        result.steering_b,
        input.dt);

    const double sqrt_argument =
        input.sqrt_input_base + 1.0 + input.global_constant_c12c24;
    require_finite(sqrt_argument, "FUN_00755a60 sqrt argument");
    if (sqrt_argument < 0.0) {
        throw std::invalid_argument("FUN_00755a60 sqrt argument must be non-negative");
    }
    const double sqrt_value = std::sqrt(sqrt_argument);
    const double ambient_exchange =
        (sqrt_value * input.ambient_coupling_a + input.ambient_coupling_b) *
        sqrt_value * input.dt;
    const double reservoir_exchange = input.reservoir_exchange * input.dt;
    require_finite(ambient_exchange, "FUN_00755a60 ambient exchange");
    require_finite(reservoir_exchange, "FUN_00755a60 reservoir exchange");

    result.reservoir_before = input.reservoir_temperature;
    double reservoir = input.reservoir_temperature;
    for (std::size_t index = 0; index < 3u; ++index) {
        const double original = input.temperatures[index];
        const double fraction = result.fractions[index];
        double value =
            original + fraction * result.source_heat +
            fraction * result.secondary_source;
        if (input.activity > 0.0) {
            value +=
                fraction * ambient_exchange * (ambient_a - original);
        }
        const double transfer =
            (reservoir - original) * reservoir_exchange;
        value += (ambient_b - original) * ambient_exchange;
        value += transfer;
        reservoir -= transfer;
        require_finite(value, "FUN_00755a60 updated temperature");
        require_finite(reservoir, "FUN_00755a60 sequential reservoir");
        result.temperatures_after[index] = value;
    }

    result.reservoir_after = clamp_value(
        reservoir,
        kWheelThermalReservoirLow,
        kWheelThermalReservoirHigh);
    result.average_temperature =
        (result.temperatures_after[0] +
         result.temperatures_after[1] +
         result.temperatures_after[2]) /
        3.0;
    require_finite(result.average_temperature, "FUN_00755a60 average temperature");

    result.derived_reservoir_field =
        result.reservoir_after * input.derived_reservoir_scale;
    require_finite(
        result.derived_reservoir_field,
        "FUN_00755a60 derived reservoir field");

    const double abrasion_temperature =
        result.average_temperature * input.average_temperature_scale;
    result.abrasion_term =
        ((std::abs(result.steering_b) + std::abs(result.steering_a) + 4.0) / 6.0) *
        input.dt * abrasion_temperature * abrasion_temperature *
        result.shape_factor * input.abrasion_scale +
        input.abrasion_accumulator;
    require_finite(result.abrasion_term, "FUN_00755a60 abrasion term");

    result.wear_after = input.wear_state;
    if (input.wear_enabled && input.wear_state > kWheelThermalWearFloor) {
        result.wear_after =
            input.wear_state - input.global_wear_scale * result.abrasion_term;
        require_finite(result.wear_after, "FUN_00755a60 wear result");
        if (result.wear_after < kWheelThermalWearFloor) {
            result.wear_after = kWheelThermalWearFloor;
            result.wear_floor_crossed = true;
        }
    }

    if (local_steering_b == 0.0) {
        throw std::invalid_argument(
            "FUN_00755a60 normalization reference must be non-zero");
    }
    const double temperature_delta =
        result.average_temperature - input.temp_reference;
    const double temperature_slope =
        temperature_delta >= 0.0
            ? input.temp_gain_positive
            : input.temp_gain_negative;
    result.normalized_temperature_delta =
        temperature_delta * temperature_slope +
        std::abs(result.derived_reservoir_field - local_steering_b) *
            input.output_limit_reference / local_steering_b;
    require_finite(
        result.normalized_temperature_delta,
        "FUN_00755a60 normalized temperature delta");
    result.limited_temperature_factor =
        std::max(1.0, result.normalized_temperature_delta);
    result.output =
        (1.0 -
         0.5 * result.limited_temperature_factor *
             result.limited_temperature_factor) *
        result.wear_after;
    require_finite(result.output, "FUN_00755a60 output");

    result.derived_auxiliary_field =
        result.derived_reservoir_field * input.derived_aux_scale +
        input.derived_aux_bias;
    require_finite(
        result.derived_auxiliary_field,
        "FUN_00755a60 derived auxiliary field");
    result.overtemperature_condition =
        result.average_temperature > input.temp_alert_threshold;
    return result;
}

}  // namespace shift::runtime::physics
