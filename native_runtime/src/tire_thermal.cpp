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
    require_finite(input.dt, "FUN_00760b50 dt");
    require_finite(input.spin_measure, "FUN_00760b50 spin measure");
    require_finite(input.spin_heat_scale, "FUN_00760b50 spin heat scale");
    require_finite(
        input.accumulated_heat_scale,
        "FUN_00760b50 accumulated heat scale");
    require_finite(
        input.speed_transfer_base,
        "FUN_00760b50 speed transfer base");
    require_finite(
        input.speed_transfer_rate,
        "FUN_00760b50 speed transfer rate");
    require_finite(
        input.longitudinal_velocity,
        "FUN_00760b50 longitudinal velocity");
    require_finite(
        input.ambient_temperature_a,
        "FUN_00760b50 ambient temperature A");
    require_finite(
        input.ambient_temperature_b,
        "FUN_00760b50 ambient temperature B");
    require_finite(input.temperature_state, "FUN_00760b50 temperature state");
    require_finite(
        input.reference_temperature,
        "FUN_00760b50 reference temperature");
    require_finite(input.thermal_reserve, "FUN_00760b50 thermal reserve");
    require_finite(
        input.reserve_depletion_capacity,
        "FUN_00760b50 reserve depletion capacity");
    require_finite(input.reserve_floor, "FUN_00760b50 reserve floor");
    require_finite(input.thermal_tolerance, "FUN_00760b50 thermal tolerance");
    require_finite(input.failure_gain_before, "FUN_00760b50 failure gain before");
    require_finite(input.failure_gain_base, "FUN_00760b50 failure gain base");
    require_finite(input.overheat_scale, "FUN_00760b50 overheat scale");
    require_finite(input.failure_rng_sample, "FUN_00760b50 failure RNG sample");
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
    require_finite(abs_spin, "FUN_00760b50 absolute spin measure");

    result.source_heat = abs_spin * input.spin_heat_scale;
    require_finite(result.source_heat, "FUN_00760b50 primary source heat");
    result.source_heat *= input.accumulated_heat_scale;
    require_finite(result.source_heat, "FUN_00760b50 accumulated source heat");

    result.abs_longitudinal =
        input.longitudinal_velocity < 0.0
            ? -input.longitudinal_velocity
            : 0.0;
    require_finite(
        result.abs_longitudinal,
        "FUN_00760b50 longitudinal magnitude");

    result.ambient_kelvin = input.ambient_temperature_a + kTireThermalKelvinBias;
    require_finite(result.ambient_kelvin, "FUN_00760b50 ambient Kelvin A");
    result.ambient_kelvin += input.ambient_temperature_b;
    require_finite(result.ambient_kelvin, "FUN_00760b50 ambient sum B");
    result.ambient_kelvin += kTireThermalKelvinBias;
    require_finite(result.ambient_kelvin, "FUN_00760b50 ambient Kelvin sum");
    result.ambient_kelvin *= 0.5;
    require_finite(result.ambient_kelvin, "FUN_00760b50 ambient Kelvin average");

    double transfer = input.speed_transfer_rate * result.abs_longitudinal;
    require_finite(transfer, "FUN_00760b50 speed transfer product");
    transfer += input.speed_transfer_base;
    require_finite(transfer, "FUN_00760b50 speed transfer affine term");

    const double ambient_delta = result.ambient_kelvin - input.temperature_state;
    require_finite(ambient_delta, "FUN_00760b50 ambient delta");
    result.convective_term = transfer * ambient_delta;
    require_finite(result.convective_term, "FUN_00760b50 convective term");

    result.net_heat = result.convective_term + result.source_heat;
    require_finite(result.net_heat, "FUN_00760b50 net heat");

    if (input.thermal_reserve <= input.reserve_floor) {
        require_nonzero(input.reserve_floor, "FUN_00760b50 reserve floor divisor");
        result.rate = result.net_heat / input.reserve_floor;
        require_finite(result.rate, "FUN_00760b50 floor-normalized rate");
    } else {
        double cubic_loss = input.reserve_depletion_capacity * result.source_heat;
        require_finite(cubic_loss, "FUN_00760b50 reserve loss stage 1");
        cubic_loss *= input.temperature_state;
        require_finite(cubic_loss, "FUN_00760b50 reserve loss stage 2");
        cubic_loss *= input.temperature_state;
        require_finite(cubic_loss, "FUN_00760b50 reserve loss stage 3");
        cubic_loss *= input.temperature_state;
        require_finite(cubic_loss, "FUN_00760b50 cubic reserve loss");

        double depletion = input.overheat_scale * cubic_loss;
        require_finite(depletion, "FUN_00760b50 scaled reserve loss");
        depletion *= input.dt;
        require_finite(depletion, "FUN_00760b50 timestep reserve loss");

        result.thermal_reserve_after = input.thermal_reserve - depletion;
        require_finite(
            result.thermal_reserve_after,
            "FUN_00760b50 thermal reserve after depletion");
        result.thermal_reserve_written = true;

        if (result.thermal_reserve_after >= input.reserve_floor) {
            require_nonzero(
                result.thermal_reserve_after,
                "FUN_00760b50 depleted reserve divisor");
            result.rate = result.net_heat / result.thermal_reserve_after;
            require_finite(result.rate, "FUN_00760b50 reserve-normalized rate");

            const double reference_delta =
                std::abs(input.temperature_state - input.reference_temperature);
            require_finite(
                reference_delta,
                "FUN_00760b50 reference temperature delta");

            if (reference_delta <= input.thermal_tolerance) {
                double failure_scale =
                    input.failure_rng_sample * kTireThermalFailureRandomWeight;
                require_finite(
                    failure_scale,
                    "FUN_00760b50 random failure gain scale");
                failure_scale += kTireThermalFailureRandomBase;
                require_finite(
                    failure_scale,
                    "FUN_00760b50 blended failure gain scale");
                result.failure_gain_after =
                    failure_scale * input.failure_gain_base;
            } else {
                result.failure_gain_after = input.failure_gain_base * 0.5;
            }
            require_finite(
                result.failure_gain_after,
                "FUN_00760b50 failure gain after");
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
        "FUN_00760b50 temperature timestep delta");
    result.temperature_after = input.temperature_state + temperature_delta;
    require_finite(
        result.temperature_after,
        "FUN_00760b50 temperature after");

    return result;
}

}  // namespace shift::runtime::physics
