#include "shift_body_export_solver_join.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::runtime_error(
                "usage: shift_runtime_body_export_solver_join_check "
                "body_solver_export.sbex solver_frame.sbfr");
        }

        using namespace shift::runtime::physics;
        const auto export_frame =
            load_prepared_body_solver_export_frame(argv[1]);
        const auto solver_frame =
            load_prepared_builtin_solver_frame(argv[2]);
        const auto result =
            join_body_export_to_builtin_solver_frame(
                export_frame,
                solver_frame);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodyExportSolverFrameJoinCheck/1\",\n"
            << "  \"body_export_source_function\": "
            << "\"FUN_007ba570\",\n"
            << "  \"reset_source_function\": "
            << "\"FUN_007b2210\",\n"
            << "  \"solve_source_function\": "
            << "\"FUN_007b0f20\",\n"
            << "  \"scalar_count\": "
            << result.scalar_count << ",\n"
            << "  \"matrix_double_count\": "
            << result.matrix_double_count << ",\n"
            << "  \"max_rhs_join_error\": "
            << std::setprecision(17)
            << result.max_rhs_join_error << ",\n"
            << "  \"max_matrix_join_error\": "
            << result.max_matrix_join_error << ",\n"
            << "  \"max_solver_oracle_error\": "
            << result.max_solver_oracle_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_export_solver_join_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
