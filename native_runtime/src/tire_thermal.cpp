#include "shift_tire_thermal.hpp"

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

void require_nonzero(double value, const char* label) {
    require_finite(value, label);
    if (value == 0.0) {
        throw std::invalid_argument(std::string(label) + " must be non-zero");
    }
}

void validate_input(const TireThermalStepInput& input) {
    require_finite(input.dt, "tire thermal dt");
    require_finite(input.spin_measure, "tire thermal spin measure");
    require_finite(input.spin_heat_scale, "tire thermal spin heat scale");
    require_finite(
        input.accumulated_heat_scale,
        "tire thermal accumulated heat scale");
    require_finite(
        input.speed_transfer_base,
        "tire thermal speed transfer base");
    require_finite(
        input.speed_transfer_rate,
        "tire thermal speed transfer rate");
    require_finite(
        input.longitudinal_velocity,
        "tire thermal longitudinal velocity");
    require_finite(
        input.ambient_temperature_a,
        "tire thermal ambient temperature A");
    require_finite(
        input.ambient_temperature_b,
        "tire thermal ambient temperature B");
    require_finite(input.temperature_state, "tire thermal temperature state");
    require_finite(
        input.reference_temperature,
        "tire thermal reference temperature");
    require_finite(input.thermal_reserve, "tire thermal thermal reserve");
    require_finite(
        input.reserve_depletion_capacity,
        "tire thermal reserve depletion capacity");
    require_finite(input.reserve_floor, "tire thermal reserve floor");
    require_finite(input.thermal_tolerance, "tire thermal thermal tolerance");
    require_finite(input.failure_gain_before, "tire thermal failure gain before");
    require_finite(input.failure_gain_base, "tire thermal failure gain base");
    require_finite(input.overheat_scale, "tire thermal overheat scale");
    require_finite(input.failure_rng_sample, "tire thermal failure RNG sample");
}

}  // namespace

TireThermalStepResult execute_fun_00760b50_thermal_step(
    const TireThermalStepInput& input) {

    validate_input(input);

    TireThermalStepResult result{};
    result.temperature_before = input.temperature_state;
    result.thermal_reserve_before = input.thermal_reserve;
    result.thermal_reserve_after = input.thermal_reserve;
    result.failure_gain_before = input.failure_gain_before;
    result.failure_gain_after = input.failure_gain_before;

    const double abs_spin = std::abs(input.spin_measure);
    require_finite(abs_spin, "tire thermal absolute spin measure");

    result.source_heat = abs_spin * input.spin_heat_scale;
    require_finite(result.source_heat, "tire thermal primary source heat");
    result.source_heat *= input.accumulated_heat_scale;
    require_finite(result.source_heat, "tire thermal accumulated source heat");

    result.abs_longitudinal =
        input.longitudinal_velocity < 0.0
            ? -input.longitudinal_velocity
            : 0.0;
    require_finite(
        result.abs_longitudinal,
        "tire thermal longitudinal magnitude");

    result.ambient_kelvin = input.ambient_temperature_a + kTireThermalKelvinBias;
    require_finite(result.ambient_kelvin, "tire thermal ambient Kelvin A");
    result.ambient_kelvin += input.ambient_temperature_b;
    require_finite(result.ambient_kelvin, "tire thermal ambient sum B");
    result.ambient_kelvin += kTireThermalKelvinBias;
    require_finite(result.ambient_kelvin, "tire thermal ambient Kelvin sum");
    result.ambient_kelvin *= 0.5;
    require_finite(result.ambient_kelvin, "tire thermal ambient Kelvin average");

    double transfer = input.speed_transfer_rate * result.abs_longitudinal;
    require_finite(transfer, "tire thermal speed transfer product");
    transfer += input.speed_transfer_base;
    require_finite(transfer, "tire thermal speed transfer affine term");

    const double ambient_delta = result.ambient_kelvin - input.temperature_state;
    require_finite(ambient_delta, "tire thermal ambient delta");
    result.convective_term = transfer * ambient_delta;
    require_finite(result.convective_term, "tire thermal convective term");

    result.net_heat = result.convective_term + result.source_heat;
    require_finite(result.net_heat, "tire thermal net heat");

    if (input.thermal_reserve <= input.reserve_floor) {
        require_nonzero(input.reserve_floor, "tire thermal reserve floor divisor");
        result.rate = result.net_heat / input.reserve_floor;
        require_finite(result.rate, "tire thermal floor-normalized rate");
    } else {
        double cubic_loss = input.reserve_depletion_capacity * result.source_heat;
        require_finite(cubic_loss, "tire thermal reserve loss stage 1");
        cubic_loss *= input.temperature_state;
        require_finite(cubic_loss, "tire thermal reserve loss stage 2");
        cubic_loss *= input.temperature_state;
        require_finite(cubic_loss, "tire thermal reserve loss stage 3");
        cubic_loss *= input.temperature_state;
        require_finite(cubic_loss, "tire thermal cubic reserve loss");

        double depletion = input.overheat_scale * cubic_loss;
        require_finite(depletion, "tire thermal scaled reserve loss");
        depletion *= input.dt;
        require_finite(depletion, "tire thermal timestep reserve loss");

        result.thermal_reserve_after = input.thermal_reserve - depletion;
        require_finite(
            result.thermal_reserve_after,
            "tire thermal thermal reserve after depletion");
        result.thermal_reserve_written = true;

        if (result.thermal_reserve_after >= input.reserve_floor) {
            require_nonzero(
                result.thermal_reserve_after,
                "tire thermal depleted reserve divisor");
            result.rate = result.net_heat / result.thermal_reserve_after;
            require_finite(result.rate, "tire thermal reserve-normalized rate");

            const double reference_delta =
                std::abs(input.temperature_state - input.reference_temperature);
            require_finite(
                reference_delta,
                "tire thermal reference temperature delta");

            if (reference_delta <= input.thermal_tolerance) {
                double failure_scale =
                    input.failure_rng_sample * kTireThermalFailureRandomWeight;
                require_finite(
                    failure_scale,
                    "tire thermal random failure gain scale");
                failure_scale += kTireThermalFailureRandomBase;
                require_finite(
                    failure_scale,
                    "tire thermal blended failure gain scale");
                result.failure_gain_after =
                    failure_scale * input.failure_gain_base;
            } else {
                result.failure_gain_after = input.failure_gain_base * 0.5;
            }
            require_finite(
                result.failure_gain_after,
                "tire thermal failure gain after");
            result.failure_gain_written = true;
        } else {
            result.thermal_reserve_after = 0.0;
            result.failure_gain_after = 0.0;
            result.failure_gain_written = true;
            result.rate = 0.0;
        }
    }

    const double temperature_delta = result.rate * input.dt;
    require_finite(
        temperature_delta,
        "tire thermal temperature timestep delta");
    result.temperature_after = input.temperature_state + temperature_delta;
    require_finite(
        result.temperature_after,
        "tire thermal temperature after");

    return result;
}

}  // namespace shift::runtime::physics
