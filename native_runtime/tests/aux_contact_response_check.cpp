#include "shift_aux_contact_response.hpp"

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

shift::runtime::physics::AuxContactResponseInput base_input() {
    using namespace shift::runtime::physics;
    AuxContactResponseInput input{};
    input.body_frame = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    input.body_transform.angular = {0.0, 0.0, 0.0};
    input.body_transform.body_position = {0.0, 0.0, 0.0};
    input.body_transform.translation = {5.0, 4.0, 1.0};
    input.reference_point = {2.0, 3.0, 5.0};
    input.record.active = true;
    input.record.point = {5.0, 4.0, 1.0};
    input.record.directional_curve = {0.0, 0.0, 0.0, 0.0};
    input.record.gain = 2.0;
    input.record.scale = 2.0;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        const auto active =
            execute_fun_00758fc0_aux_contact_response(base_input());
        if (!active.applied) {
            throw std::runtime_error("FUN_00758fc0 active branch not applied");
        }
        const double expected_record_point[3] = {5.0, 4.0, 1.0};
        const double expected_relative[3] = {3.0, 1.0, -4.0};
        const double expected_response[3] = {0.0, 32.0, 32.0};
        const double expected_angular[3] = {96.0, -160.0, 160.0};
        const double expected_linear[3] = {0.0, 32.0, 32.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                active.transformed_record_point[component],
                expected_record_point[component],
                0.0,
                "FUN_00758fc0 transformed record point",
                max_error);
            require_close(
                active.relative_point[component],
                expected_relative[component],
                0.0,
                "FUN_00758fc0 relative point",
                max_error);
            require_close(
                active.local_response[component],
                expected_response[component],
                0.0,
                "FUN_00758fc0 local response",
                max_error);
            require_close(
                active.transformed_response[component],
                expected_response[component],
                0.0,
                "FUN_00758fc0 transformed response",
                max_error);
            require_close(
                active.body_accumulator.angular[component],
                expected_angular[component],
                0.0,
                "FUN_00758fc0 BODY angular accumulator",
                max_error);
            require_close(
                active.body_accumulator.linear[component],
                expected_linear[component],
                0.0,
                "FUN_00758fc0 BODY linear accumulator",
                max_error);
        }
        require_close(
            active.square_negative_z,
            16.0,
            0.0,
            "FUN_00758fc0 squared negative z",
            max_error);
        require_close(
            active.directional_multiplier,
            1.0,
            0.0,
            "FUN_00758fc0 directional multiplier",
            max_error);

        auto inactive_input = base_input();
        inactive_input.record.active = false;
        inactive_input.body_accumulator.angular = {1.0, 2.0, 3.0};
        inactive_input.body_accumulator.linear = {4.0, 5.0, 6.0};
        const auto inactive =
            execute_fun_00758fc0_aux_contact_response(inactive_input);
        if (inactive.applied || inactive.square_negative_z != 0.0) {
            throw std::runtime_error("FUN_00758fc0 inactive gate mismatch");
        }
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                inactive.body_accumulator.angular[component],
                inactive_input.body_accumulator.angular[component],
                0.0,
                "FUN_00758fc0 inactive angular preservation",
                max_error);
            require_close(
                inactive.body_accumulator.linear[component],
                inactive_input.body_accumulator.linear[component],
                0.0,
                "FUN_00758fc0 inactive linear preservation",
                max_error);
        }

        auto nonnegative_input = base_input();
        nonnegative_input.reference_point = {2.0, 3.0, 0.0};
        const auto nonnegative =
            execute_fun_00758fc0_aux_contact_response(nonnegative_input);
        if (nonnegative.applied || nonnegative.relative_point[2] < 0.0) {
            throw std::runtime_error("FUN_00758fc0 nonnegative-z gate mismatch");
        }

        bool non_finite_rejected = false;
        try {
            auto bad = base_input();
            bad.reference_point[0] = std::numeric_limits<double>::infinity();
            (void)execute_fun_00758fc0_aux_contact_response(bad);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "FUN_00758fc0 accepted non-finite input");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeAuxContactResponse/1\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00758fc0\","
            << "\"forward_transform\":\"FUN_007aefb0\","
            << "\"point_transform\":\"FUN_007537b0\","
            << "\"reverse_transform\":\"FUN_007af0a0\","
            << "\"directional_function\":\"FUN_00755340\","
            << "\"accumulator_function\":\"FUN_007baa70\","
            << "\"active_application_proven\":true,"
            << "\"inactive_gate_proven\":true,"
            << "\"nonnegative_z_gate_proven\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
