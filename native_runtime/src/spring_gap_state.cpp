#include "shift_spring_gap_state.hpp"

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

}  // namespace

double compute_fun_007555b0_gap(
    double displacement,
    double lower_boundary,
    double upper_boundary) {

    require_finite(displacement, "FUN_007555b0 displacement");
    require_finite(lower_boundary, "FUN_007555b0 lower boundary");
    require_finite(upper_boundary, "FUN_007555b0 upper boundary");

    const double result =
        displacement <= upper_boundary
            ? upper_boundary - displacement
            : displacement - lower_boundary;
    require_finite(result, "FUN_007555b0 gap result");
    return result;
}

SpringGapStateResult execute_fun_007555b0_gap_state(
    const SpringGapStateInput& input) {

    if (input.spring_type < 0) {
        throw std::invalid_argument("FUN_007555b0 spring type must be non-negative");
    }
    require_finite(input.current_gap_before, "FUN_007555b0 current gap before");
    require_finite(input.trigger_value, "FUN_007555b0 trigger value");

    SpringGapStateResult result{};
    result.spring_type = input.spring_type;

    // Retail first copies +0x248 to +0x250, then recalculates +0x248.
    result.previous_gap_after = input.current_gap_before;
    result.current_gap_after = compute_fun_007555b0_gap(
        input.displacement,
        input.lower_boundary,
        input.upper_boundary);

    result.crossing_transition =
        result.current_gap_after > 0.0 &&
        result.previous_gap_after < 0.0;

    // The recovered instruction stream proves writes on the transition. It does
    // not prove that either field is cleared on the non-transition path.
    if (result.crossing_transition) {
        result.crossing_flag_set = true;
        result.trigger_value_written = input.trigger_value;
    }
    return result;
}

}  // namespace shift::runtime::physics
