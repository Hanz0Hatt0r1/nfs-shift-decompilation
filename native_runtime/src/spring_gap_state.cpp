#include "shift_spring_gap_state.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

double require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(label) + " must be finite");
    }
    return value;
}

}  // namespace

double compute_fun_007555b0_gap(
    double displacement,
    double lower_boundary,
    double upper_boundary) {

    displacement = require_finite(displacement, "FUN_007555b0 displacement");
    lower_boundary = require_finite(
        lower_boundary,
        "FUN_007555b0 lower boundary");
    upper_boundary = require_finite(
        upper_boundary,
        "FUN_007555b0 upper boundary");

    const double current_gap = displacement <= upper_boundary
        ? upper_boundary - displacement
        : displacement - lower_boundary;
    return require_finite(current_gap, "FUN_007555b0 current gap");
}

SpringGapStateResult execute_fun_007555b0_gap_state(
    const SpringGapStateInput& input) {

    if (input.spring_type < 0) {
        throw std::invalid_argument(
            "FUN_007555b0 spring type must be non-negative");
    }

    const double previous_gap = require_finite(
        input.previous_gap,
        "FUN_007555b0 previous gap");
    const double trigger_value = require_finite(
        input.trigger_value,
        "FUN_007555b0 trigger value");
    const double displacement = require_finite(
        input.displacement,
        "FUN_007555b0 displacement");
    const double current_gap = compute_fun_007555b0_gap(
        displacement,
        input.lower_boundary,
        input.upper_boundary);
    const bool transition_triggered =
        current_gap > 0.0 && previous_gap < 0.0;

    SpringGapStateResult result{};
    result.spring_type = input.spring_type;
    result.displacement = displacement;
    result.previous_gap = previous_gap;
    result.current_gap = current_gap;
    result.transition_triggered = transition_triggered;
    if (transition_triggered) {
        result.trigger_value = trigger_value;
    }
    return result;
}

}  // namespace shift::runtime::physics
