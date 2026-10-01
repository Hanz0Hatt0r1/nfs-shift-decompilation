#include "shift_generated_body_solver_frame_join.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv) {
    try {
        using namespace shift::runtime::physics;
        if (argc != 3) {
            std::cerr
                << "usage: shift_runtime_generated_body_solver_frame_join_check "
                << "FRAME.gbcf SOLVER.sbfr\n";
            return EXIT_FAILURE;
        }

        const auto generated =
            load_prepared_generated_body_constraint_frame(
                argv[1]);
        const auto solver =
            load_prepared_builtin_solver_frame(
                argv[2]);
        const auto result =
            join_generated_body_constraints_to_builtin_solver_frame(
                generated,
                solver);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeGeneratedBodySolverFrameJoinCheck/1\",\n"
            << "  \"generated_packet\": \"GBCF\",\n"
            << "  \"solver_packet\": \"SBFR\",\n"
            << "  \"generation_function\": \"FUN_007bc680\",\n"
            << "  \"storage_function\": \"FUN_007bb8d0\",\n"
            << "  \"export_function\": \"FUN_007ba570\",\n"
            << "  \"reset_function\": \"FUN_007b2210\",\n"
            << "  \"solve_function\": \"FUN_007b0f20\",\n"
            << "  \"scalar_count\": "
            << result.scalar_count << ",\n"
            << "  \"matrix_double_count\": "
            << result.matrix_double_count << ",\n"
            << "  \"body_count\": "
            << result.body_count << ",\n"
            << "  \"max_rhs_join_error\": "
            << std::setprecision(17)
            << result.max_rhs_join_error << ",\n"
            << "  \"max_matrix_join_error\": "
            << result.max_matrix_join_error << ",\n"
            << "  \"max_solver_oracle_error\": "
            << result.max_solver_oracle_error << ",\n"
            << "  \"contribution_values_stored_in_gbcf\": false,\n"
            << "  \"join_before_reset_solve\": true,\n"
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
