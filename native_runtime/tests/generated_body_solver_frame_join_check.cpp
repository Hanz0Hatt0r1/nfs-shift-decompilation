#include "shift_generated_body_constraint_frame.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        using namespace shift::runtime::physics;
        if (argc != 3) {
            std::cerr
                << "usage: shift_runtime_generated_body_solver_frame_join_check "
                << "generated_body_constraints.gbcf solver_frame.sbfr\n";
            return EXIT_FAILURE;
        }

        const auto generated_frame =
            load_prepared_generated_body_constraint_frame(argv[1]);
        const auto solver_frame =
            load_prepared_builtin_solver_frame(argv[2]);
        const auto result =
            verify_generated_body_constraint_frame_matches_builtin_solver_frame(
                generated_frame,
                solver_frame);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeGeneratedBodySolverFrameJoinCheck/1\",\n"
            << "  \"generation_function\": \"FUN_007bc680\",\n"
            << "  \"storage_function\": \"FUN_007bb8d0\",\n"
            << "  \"export_function\": \"FUN_007ba570\",\n"
            << "  \"reset_function\": \"FUN_007b2210\",\n"
            << "  \"solve_function\": \"FUN_007b0f20\",\n"
            << "  \"scalar_count\": " << result.scalar_count << ",\n"
            << "  \"matrix_double_count\": "
            << result.matrix_double_count << ",\n"
            << "  \"body_count\": " << result.body_count << ",\n"
            << "  \"joint_samples\": "
            << result.joint_sample_count << ",\n"
            << "  \"hinge_samples\": "
            << result.hinge_sample_count << ",\n"
            << "  \"bar_samples\": "
            << result.bar_sample_count << ",\n"
            << "  \"contribution_values_stored_in_gbcf\": false,\n"
            << "  \"native_generation_executed\": true,\n"
            << "  \"max_rhs_join_error\": "
            << std::setprecision(17)
            << result.max_rhs_join_error << ",\n"
            << "  \"max_matrix_join_error\": "
            << result.max_matrix_join_error << ",\n"
            << "  \"join_tolerance\": 1e-12,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_generated_body_solver_frame_join_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
