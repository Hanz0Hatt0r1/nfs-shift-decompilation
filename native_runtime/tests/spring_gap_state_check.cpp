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

        if (kSpringGapLowerBoundaryOffset != 0x238u ||
            kSpringGapUpperBoundaryOffset != 0x240u ||
            kSpringGapCurrentOffset != 0x248u ||
            kSpringGapPreviousOffset != 0x250u ||
            kSpringGapTriggerValueOffset != 0x258u ||
            kSpringGapCrossingFlagOffset != 0x260u) {
            throw std::runtime_error("FUN_007555b0 state offsets mismatch");
        }

        require_close(
            compute_fun_007555b0_gap(5.0, 2.0, 5.0),
            0.0,
            0.0,
            "upper-bound equality branch",
            max_error);
        require_close(
            compute_fun_007555b0_gap(4.0, 2.0, 5.0),
            1.0,
            0.0,
            "upper-minus-displacement branch",
            max_error);
        require_close(
            compute_fun_007555b0_gap(7.0, 2.0, 5.0),
            5.0,
            0.0,
            "displacement-minus-lower branch",
            max_error);

        SpringGapStateInput crossing_input{};
        crossing_input.spring_type = 0;
        crossing_input.displacement = 4.0;
        crossing_input.lower_boundary = 2.0;
        crossing_input.upper_boundary = 5.0;
        crossing_input.current_gap_before = -0.25;
        crossing_input.trigger_value = -3.5;
        const auto crossing = execute_fun_007555b0_gap_state(crossing_input);
        require_close(
            crossing.previous_gap_after,
            -0.25,
            0.0,
            "+0x248 to +0x250 copy",
            max_error);
        require_close(
            crossing.current_gap_after,
            1.0,
            0.0,
            "+0x248 recalculation",
            max_error);
        if (!crossing.crossing_transition || !crossing.crossing_flag_set ||
            !crossing.trigger_value_written.has_value()) {
            throw std::runtime_error("positive-over-negative crossing was not latched");
        }
        require_close(
            *crossing.trigger_value_written,
            -3.5,
            0.0,
            "+0x258 trigger write",
            max_error);

        SpringGapStateInput non_crossing_input{};
        non_crossing_input.spring_type = 2;
        non_crossing_input.displacement = 6.0;
        non_crossing_input.lower_boundary = 2.0;
        non_crossing_input.upper_boundary = 5.0;
        non_crossing_input.current_gap_before = 1.0;
        non_crossing_input.trigger_value = 4.0;
        const auto non_crossing =
            execute_fun_007555b0_gap_state(non_crossing_input);
        require_close(
            non_crossing.previous_gap_after,
            1.0,
            0.0,
            "non-crossing previous gap",
            max_error);
        require_close(
            non_crossing.current_gap_after,
            4.0,
            0.0,
            "non-crossing current gap",
            max_error);
        if (non_crossing.crossing_transition || non_crossing.crossing_flag_set ||
            non_crossing.trigger_value_written.has_value()) {
            throw std::runtime_error(
                "non-crossing path invented crossing-field writes");
        }

        bool negative_type_rejected = false;
        try {
            auto invalid = crossing_input;
            invalid.spring_type = -1;
            (void)execute_fun_007555b0_gap_state(invalid);
        } catch (const std::invalid_argument&) {
            negative_type_rejected = true;
        }
        if (!negative_type_rejected) {
            throw std::runtime_error("negative spring type was accepted");
        }

        bool non_finite_rejected = false;
        try {
            (void)compute_fun_007555b0_gap(
                std::numeric_limits<double>::quiet_NaN(),
                1.0,
                2.0);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite spring gap input was accepted");
        }

        bool overflow_rejected = false;
        try {
            (void)compute_fun_007555b0_gap(
                std::numeric_limits<double>::max(),
                -std::numeric_limits<double>::max(),
                0.0);
        } catch (const std::invalid_argument&) {
            overflow_rejected = true;
        }
        if (!overflow_rejected) {
            throw std::runtime_error("non-finite spring gap result was accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeSpringGapStateFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_007555b0\","
            << "\"caller\":\"FUN_00755950\","
            << "\"gap_expression_proven\":true,"
            << "\"gap_history_write_proven\":true,"
            << "\"crossing_transition_write_proven\":true,"
            << "\"non_transition_clear_proven\":false,"
            << "\"caller_x87_return_proven\":false,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
