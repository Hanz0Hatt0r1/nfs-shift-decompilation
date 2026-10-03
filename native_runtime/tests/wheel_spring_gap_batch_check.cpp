#include "shift_wheel_spring_gap_batch.hpp"

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

shift::runtime::physics::WheelSpringGapBatchSlotInput make_slot(
    bool skip,
    shift::runtime::physics::WheelKinematicsVector3d relative,
    double reference,
    double projection,
    double lower,
    double upper,
    double previous,
    int spring_type = 0) {

    using namespace shift::runtime::physics;
    WheelSpringGapBatchSlotInput slot{};
    slot.kinematic.skip_flag_nonzero = skip;
    slot.kinematic.relative_vector = relative;
    slot.kinematic.reference_length = reference;
    slot.kinematic.projection_input = projection;
    slot.spring_type = spring_type;
    slot.lower_boundary = lower;
    slot.upper_boundary = upper;
    slot.current_gap_before = previous;
    return slot;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        std::array<WheelSpringGapBatchSlotInput, kWheelKinematicsCount> inputs{};
        inputs[0] = make_slot(
            false, {3.0, 4.0, 0.0}, 7.0, -1.5, 0.0, 3.0, -0.25);
        // A skipped zero vector proves that the retail +0xf8 gate executes before
        // relative-vector normalization and the FUN_00755950 path.
        inputs[1] = make_slot(
            true, {0.0, 0.0, 0.0}, 0.0, 0.0, 0.0, 0.0, 0.0);
        inputs[2] = make_slot(
            false, {0.0, 0.0, 2.0}, 1.0, 0.25, -2.0, 0.5, 0.5);
        inputs[3] = make_slot(
            false, {1.0, 2.0, 2.0}, 10.0, -4.0, 1.0, 6.0, -2.0);

        const auto result = execute_fun_00758b50_spring_gap_batch(inputs);
        if (result.processed_count != 3u ||
            !result.processed[0] || result.processed[1] ||
            !result.processed[2] || !result.processed[3]) {
            throw std::runtime_error("batch processed mask mismatch");
        }
        if (result.processed_order[0] != 0u ||
            result.processed_order[1] != 2u ||
            result.processed_order[2] != 3u) {
            throw std::runtime_error("retail wheel order mismatch");
        }
        if (result.kinematics[1].has_value() ||
            result.spring_results[1].has_value()) {
            throw std::runtime_error("skipped slot produced downstream state");
        }

        const auto& first_kin = result.kinematics[0].value();
        const auto& first_spring = result.spring_results[0].value();
        require_close(first_kin.relative_length, 5.0, 0.0, "wheel 0 length", max_error);
        require_close(first_spring.displacement, 2.0, 0.0, "wheel 0 displacement", max_error);
        require_close(first_spring.trigger_value, 1.5, 0.0, "wheel 0 trigger", max_error);
        require_close(
            first_spring.spring_state.previous_gap_after,
            -0.25,
            0.0,
            "wheel 0 previous gap",
            max_error);
        require_close(
            first_spring.spring_state.current_gap_after,
            1.0,
            0.0,
            "wheel 0 current gap",
            max_error);
        if (!first_spring.spring_state.crossing_transition ||
            !first_spring.spring_state.crossing_flag_set ||
            !first_spring.spring_state.trigger_value_written.has_value()) {
            throw std::runtime_error("wheel 0 crossing transition mismatch");
        }

        const auto& third_spring = result.spring_results[2].value();
        require_close(third_spring.displacement, -1.0, 0.0, "wheel 2 displacement", max_error);
        require_close(
            third_spring.spring_state.current_gap_after,
            1.5,
            0.0,
            "wheel 2 current gap",
            max_error);
        if (third_spring.spring_state.crossing_transition ||
            third_spring.spring_state.crossing_flag_set ||
            third_spring.spring_state.trigger_value_written.has_value()) {
            throw std::runtime_error("wheel 2 non-crossing path invented writes");
        }

        const auto& fourth_spring = result.spring_results[3].value();
        require_close(fourth_spring.displacement, 7.0, 0.0, "wheel 3 displacement", max_error);
        require_close(
            fourth_spring.spring_state.current_gap_after,
            6.0,
            0.0,
            "wheel 3 current gap",
            max_error);
        if (!fourth_spring.spring_state.trigger_value_written.has_value()) {
            throw std::runtime_error("wheel 3 trigger write missing");
        }
        require_close(
            *fourth_spring.spring_state.trigger_value_written,
            4.0,
            0.0,
            "wheel 3 trigger write",
            max_error);

        bool non_finite_rejected = false;
        try {
            auto invalid = inputs;
            invalid[2].kinematic.relative_vector[0] =
                std::numeric_limits<double>::infinity();
            (void)execute_fun_00758b50_spring_gap_batch(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("active non-finite slot was accepted");
        }

        bool spring_type_rejected = false;
        try {
            auto invalid = inputs;
            invalid[0].spring_type = -1;
            (void)execute_fun_00758b50_spring_gap_batch(invalid);
        } catch (const std::invalid_argument&) {
            spring_type_rejected = true;
        }
        if (!spring_type_rejected) {
            throw std::runtime_error("negative spring type was accepted");
        }

        bool zero_vector_rejected = false;
        try {
            auto invalid = inputs;
            invalid[0].kinematic.relative_vector = {0.0, 0.0, 0.0};
            (void)execute_fun_00758b50_spring_gap_batch(invalid);
        } catch (const std::invalid_argument&) {
            zero_vector_rejected = true;
        }
        if (!zero_vector_rejected) {
            throw std::runtime_error("active zero relative vector was accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeWheelSpringGapBatchFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00758b50\","
            << "\"wheel_count\":4,"
            << "\"fixture_processed_count\":" << result.processed_count << ","
            << "\"retail_iteration_order_proven\":true,"
            << "\"skip_gate_before_payload_proven\":true,"
            << "\"kinematics_spring_join_proven\":true,"
            << "\"active_non_finite_rejected\":true,"
            << "\"fixed_size_typed_contract\":true,"
            << "\"caller_x87_return_external\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
