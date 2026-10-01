#include "shift_generated_body_constraint_frame.hpp"

#include <algorithm>
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
    for (std::size_t index = 0;
         index < actual.size();
         ++index) {
        const double error =
            std::abs(actual[index] - expected[index]);
        observed_max =
            std::max(observed_max, error);
        if (error > tolerance) {
            throw std::runtime_error(
                std::string(label) +
                " mismatch at index " +
                std::to_string(index));
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        using namespace shift::runtime::physics;
        if (argc != 2) {
            std::cerr
                << "usage: shift_runtime_generated_body_constraint_frame_check "
                << "FILE.gbcf\n";
            return EXIT_FAILURE;
        }

        const auto frame =
            load_prepared_generated_body_constraint_frame(
                argv[1]);
        const auto result =
            execute_prepared_generated_body_constraint_frame(
                frame);

        const std::vector<double> expected_vector = {
            7.125,
            15.0,
            20.3125,
            9.125,
            20.75,
            52.5,
        };
        const std::vector<double> expected_matrix = {
            19.5, 0.0, 0.0, 0.0, 0.0, 0.0,
            -3.75, 15.5, 0.0, 0.0, 0.0, 0.0,
            -5.25, -8.75, 9.5, 0.0, 0.0, 0.0,
            -0.5, 1.0, -0.5, 14.0, 0.0, 0.0,
            2.5, -5.0, 2.5, 32.0, 77.0, 0.0,
            -3.0, 24.0, -13.0, 6.0, 3.0, 41.0,
        };

        double max_absolute_error = 0.0;
        require_close(
            result.solver_vector,
            expected_vector,
            1e-12,
            "generated frame solver vector",
            max_absolute_error);
        require_close(
            result.solver_matrix,
            expected_matrix,
            1e-12,
            "generated frame solver matrix",
            max_absolute_error);

        if (frame.scalar_count != 6u ||
            frame.matrix_double_count != 36u ||
            result.body_count != 1u ||
            result.joint_sample_count != 1u ||
            result.hinge_sample_count != 1u ||
            result.bar_sample_count != 1u) {
            throw std::runtime_error(
                "generated BODY constraint frame counts mismatch");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeGeneratedBodyConstraintFrameCheck/1\",\n"
            << "  \"packet_format\": "
            << "\"SHIFT.NativeGeneratedBodyConstraintFramePacket/1\",\n"
            << "  \"generation_function\": \"FUN_007bc680\",\n"
            << "  \"storage_function\": \"FUN_007bb8d0\",\n"
            << "  \"export_function\": \"FUN_007ba570\",\n"
            << "  \"body_count\": 1,\n"
            << "  \"scalar_count\": 6,\n"
            << "  \"matrix_double_count\": 36,\n"
            << "  \"joint_samples\": 1,\n"
            << "  \"hinge_samples\": 1,\n"
            << "  \"bar_samples\": 1,\n"
            << "  \"contribution_values_stored_in_packet\": false,\n"
            << "  \"native_generation_executed\": true,\n"
            << "  \"provider_present\": false,\n"
            << "  \"sampled_state_refresh_executed\": false,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_generated_body_constraint_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
