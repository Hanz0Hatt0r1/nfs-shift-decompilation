#include "shift_wheel_spring_gap_join.hpp"

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

shift::runtime::physics::WheelKinematicObservation make_kinematic() {
    using namespace shift::runtime::physics;
    WheelKinematicSlotInput input{};
    input.relative_vector = {3.0, 4.0, 12.0};
    input.reference_length = 15.0;
    input.projection_input = -2.0;
    return prepare_fun_00758b50_wheel_kinematics(2u, input);
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        WheelSpringGapJoinInput input{};
        input.kinematic = make_kinematic();
        input.spring_type = 0;
        input.lower_boundary = 0.0;
        input.upper_boundary = 3.0;
        input.current_gap_before = -0.25;

        const auto result = execute_fun_00755950_spring_gap_join(input);
        if (result.wheel_index != 2u) {
            throw std::runtime_error("wheel index was not preserved");
        }
        require_close(result.displacement, 2.0, 0.0, "joined displacement", max_error);
        require_close(result.trigger_value, 2.0, 0.0, "joined trigger", max_error);
        require_close(
            result.spring_state.previous_gap_after,
            -0.25,
            0.0,
            "joined previous gap",
            max_error);
        require_close(
            result.spring_state.current_gap_after,
            1.0,
            0.0,
            "joined current gap",
            max_error);
        if (!result.spring_state.crossing_transition ||
            !result.spring_state.crossing_flag_set ||
            !result.spring_state.trigger_value_written.has_value()) {
            throw std::runtime_error("joined crossing transition not preserved");
        }
        require_close(
            *result.spring_state.trigger_value_written,
            2.0,
            0.0,
            "joined trigger write",
            max_error);

        auto non_crossing_input = input;
        non_crossing_input.lower_boundary = 0.0;
        non_crossing_input.upper_boundary = 1.0;
        non_crossing_input.current_gap_before = 0.5;
        const auto non_crossing =
            execute_fun_00755950_spring_gap_join(non_crossing_input);
        require_close(
            non_crossing.spring_state.current_gap_after,
            2.0,
            0.0,
            "joined non-crossing gap",
            max_error);
        if (non_crossing.spring_state.crossing_transition ||
            non_crossing.spring_state.crossing_flag_set ||
            non_crossing.spring_state.trigger_value_written.has_value()) {
            throw std::runtime_error("joined non-crossing path invented writes");
        }

        bool topology_rejected = false;
        try {
            auto invalid = input;
            invalid.kinematic.wheel_runtime_offset += 8u;
            (void)execute_fun_00755950_spring_gap_join(invalid);
        } catch (const std::invalid_argument&) {
            topology_rejected = true;
        }
        if (!topology_rejected) {
            throw std::runtime_error("mismatched wheel topology was accepted");
        }

        bool displacement_rejected = false;
        try {
            auto invalid = input;
            invalid.kinematic.distance_error += 1.0;
            (void)execute_fun_00755950_spring_gap_join(invalid);
        } catch (const std::invalid_argument&) {
            displacement_rejected = true;
        }
        if (!displacement_rejected) {
            throw std::runtime_error("mismatched distance handoff was accepted");
        }

        bool projection_rejected = false;
        try {
            auto invalid = input;
            invalid.kinematic.stored_projection_value = -9.0;
            (void)execute_fun_00755950_spring_gap_join(invalid);
        } catch (const std::invalid_argument&) {
            projection_rejected = true;
        }
        if (!projection_rejected) {
            throw std::runtime_error("mismatched projection handoff was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = input;
            invalid.current_gap_before = std::numeric_limits<double>::infinity();
            (void)execute_fun_00755950_spring_gap_join(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite spring state was accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeWheelSpringGapJoinFormat << "\","
            << "\"ready\":true,"
            << "\"caller\":\"FUN_00755950\","
            << "\"kinematics_function\":\"FUN_00758b50\","
            << "\"spring_function\":\"FUN_007555b0\","
            << "\"distance_error_join_proven\":true,"
            << "\"projection_trigger_join_proven\":true,"
            << "\"cross_contract_identity_gate_proven\":true,"
            << "\"caller_x87_return_external\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
