#include "shift_spring_gap_state.hpp"

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

}  // namespace

int main() {
    using namespace shift::runtime::physics;

    try {
        double max_error = 0.0;

        if (kSpringGapCurrentOffset != 0x248u ||
            kSpringGapPreviousOffset != 0x250u ||
            kSpringGapTriggerOffset != 0x258u ||
            kSpringGapCrossingFlagOffset != 0x260u ||
            kSpringGapLowerBoundaryOffset != 0x238u ||
            kSpringGapUpperBoundaryOffset != 0x240u) {
            throw std::runtime_error("FUN_007555b0 source layout mismatch");
        }

        require_close(
            compute_fun_007555b0_gap(-2.0, -1.0, 1.0),
            3.0,
            0.0,
            "FUN_007555b0 upper-side expression mismatch",
            max_error);
        require_close(
            compute_fun_007555b0_gap(2.0, -1.0, 1.0),
            3.0,
            0.0,
            "FUN_007555b0 lower-side expression mismatch",
            max_error);
        require_close(
            compute_fun_007555b0_gap(1.0, -1.0, 1.0),
            0.0,
            0.0,
            "FUN_007555b0 <= branch boundary mismatch",
            max_error);

        SpringGapStateInput transition_input{};
        transition_input.spring_type = 2;
        transition_input.displacement = -2.0;
        transition_input.lower_boundary = -1.0;
        transition_input.upper_boundary = 1.0;
        transition_input.previous_gap = -0.25;
        transition_input.trigger_value = 7.5;
        const auto transition = execute_fun_007555b0_gap_state(transition_input);
        if (!transition.transition_triggered || !transition.trigger_value.has_value()) {
            throw std::runtime_error("FUN_007555b0 crossing transition was not preserved");
        }
        require_close(
            transition.current_gap,
            3.0,
            0.0,
            "FUN_007555b0 current gap mismatch",
            max_error);
        require_close(
            *transition.trigger_value,
            7.5,
            0.0,
            "FUN_007555b0 trigger value mismatch",
            max_error);

        auto no_transition_input = transition_input;
        no_transition_input.previous_gap = 0.25;
        const auto no_transition = execute_fun_007555b0_gap_state(no_transition_input);
        if (no_transition.transition_triggered || no_transition.trigger_value.has_value()) {
            throw std::runtime_error("FUN_007555b0 fabricated a non-crossing transition");
        }

        auto zero_current_input = transition_input;
        zero_current_input.displacement = zero_current_input.upper_boundary;
        const auto zero_current = execute_fun_007555b0_gap_state(zero_current_input);
        if (zero_current.transition_triggered) {
            throw std::runtime_error("FUN_007555b0 treated zero current gap as positive");
        }

        bool negative_type_rejected = false;
        try {
            auto invalid = transition_input;
            invalid.spring_type = -1;
            (void)execute_fun_007555b0_gap_state(invalid);
        } catch (const std::invalid_argument&) {
            negative_type_rejected = true;
        }
        if (!negative_type_rejected) {
            throw std::runtime_error("FUN_007555b0 accepted negative spring type");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = transition_input;
            invalid.previous_gap = std::numeric_limits<double>::quiet_NaN();
            (void)execute_fun_007555b0_gap_state(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("FUN_007555b0 accepted non-finite state");
        }

        bool overflow_rejected = false;
        try {
            (void)compute_fun_007555b0_gap(
                -std::numeric_limits<double>::max(),
                -1.0,
                std::numeric_limits<double>::max());
        } catch (const std::invalid_argument&) {
            overflow_rejected = true;
        }
        if (!overflow_rejected) {
            throw std::runtime_error("FUN_007555b0 accepted non-finite arithmetic result");
        }

        std::cout
            << "{\"format\":\"" << kNativeSpringGapStateFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"" << kSpringGapFunction << "\","
            << "\"caller\":\"" << kSpringGapCallerFunction << "\","
            << "\"gap_arithmetic_proven\":true,"
            << "\"history_transition_proven\":true,"
            << "\"caller_x87_return_implemented\":false,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
