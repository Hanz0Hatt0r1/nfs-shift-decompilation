#include "shift_body_constraint_assembly.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require_close(
    const std::vector<double>& actual,
    const std::vector<double>& expected,
    double tolerance,
    const char* label,
    double& observed_max) {

    if (actual.size() != expected.size()) {
        throw std::runtime_error(
            std::string(label) + " cardinality mismatch");
    }
    for (std::size_t index = 0; index < actual.size(); ++index) {
        const double error =
            std::abs(actual[index] - expected[index]);
        observed_max = std::max(observed_max, error);
        if (error > tolerance) {
            throw std::runtime_error(
                std::string(label) + " mismatch at index " +
                std::to_string(index));
        }
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;
        double max_absolute_error = 0.0;

        BodyConstraintAssemblyInput input{};
        input.scalar_count = 6u;
        input.body_position = {1.0, 2.0, 3.0};
        input.preprojection.body_correction = {0.0, 0.0, 0.0};
        input.preprojection.body_axis = {0.25, 0.5, 0.75};
        input.preprojection.angular_state = {0.125, 0.25, 0.5};
        input.preprojection.linear_state = {0.5, 0.75, 1.0};
        input.preprojection.inverse_scalar = 1.0;
        input.preprojection.body_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        input.body_tensor = {{
            {{1.0, 0.0, 0.0}},
            {{0.0, 1.0, 0.0}},
            {{0.0, 0.0, 1.0}},
        }};
        input.scales.linear_scale = 2.0;
        input.scales.quadratic_scale = 3.0;

        input.joints.push_back({
            {1.5, 2.5, 3.5},
            0u,
            0u,
        });
        input.hinges.push_back({
            {1.0, 2.0, 3.0},
            {4.0, 5.0, 6.0},
            {1.0, 2.0, 3.0},
            {0.5, 1.0, 1.5},
            3u,
            0u,
        });
        input.bars.push_back({
            {2.0, 1.0, 3.0},
            {1.0, 2.0, 1.0},
            0.5,
            5u,
            0u,
        });

        const auto result =
            assemble_fun_007bc680_body_constraints(input);

        require_close(
            result.solver_vector,
            {
                7.125,
                15.0,
                20.3125,
                9.125,
                20.75,
                52.5,
            },
            1e-12,
            "BODY solver-vector orchestration",
            max_absolute_error);

        require_close(
            result.lower_matrix,
            {
                19.5, 0.0, 0.0, 0.0, 0.0, 0.0,
                -3.75, 15.5, 0.0, 0.0, 0.0, 0.0,
                -5.25, -8.75, 9.5, 0.0, 0.0, 0.0,
                -0.5, 1.0, -0.5, 14.0, 0.0, 0.0,
                2.5, -5.0, 2.5, 32.0, 77.0, 0.0,
                -3.0, 24.0, -13.0, 6.0, 3.0, 41.0,
            },
            1e-12,
            "BODY lower-triangle matrix orchestration",
            max_absolute_error);

        if (result.joint_projection_count != 1u ||
            result.hinge_projection_count != 1u ||
            result.bar_projection_count != 1u ||
            result.joint_matrix_self_count != 1u ||
            result.joint_matrix_pair_count != 2u ||
            result.hinge_matrix_self_count != 1u ||
            result.hinge_matrix_pair_count != 0u ||
            result.hinge_bar_pair_count != 1u ||
            result.bar_matrix_self_count != 1u ||
            result.bar_matrix_pair_count != 0u) {
            throw std::runtime_error(
                "BODY orchestration stage counts mismatch");
        }

        bool overlap_rejected = false;
        try {
            auto invalid = input;
            invalid.hinges[0].scalar_base = 2u;
            (void)assemble_fun_007bc680_body_constraints(
                invalid);
        } catch (const std::invalid_argument&) {
            overlap_rejected = true;
        }
        if (!overlap_rejected) {
            throw std::runtime_error(
                "overlapping scalar ranges were accepted");
        }

        bool range_rejected = false;
        try {
            auto invalid = input;
            invalid.bars[0].scalar_base = 6u;
            (void)assemble_fun_007bc680_body_constraints(
                invalid);
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "out-of-domain scalar range was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodyConstraintAssemblyCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bc680\",\n"
            << "  \"projection_order\": "
            << "\"JOINT,HINGE,BAR\",\n"
            << "  \"matrix_order\": "
            << "\"FUN_007bbb80,FUN_007bb250,FUN_007bb6c0\",\n"
            << "  \"scalar_count\": 6,\n"
            << "  \"joint_samples\": 1,\n"
            << "  \"hinge_samples\": 1,\n"
            << "  \"bar_samples\": 1,\n"
            << "  \"projection_writes\": 3,\n"
            << "  \"matrix_self_writes\": 3,\n"
            << "  \"matrix_pair_writes\": 3,\n"
            << "  \"overlap_rejected\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"oracle_within_tolerance\": true,\n"
            << "  \"sampled_state_refresh_executed\": false,\n"
            << "  \"sparse_row_pointer_write_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_constraint_assembly_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
