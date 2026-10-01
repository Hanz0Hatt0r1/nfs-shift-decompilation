#include "shift_body_solver_export_frame.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error(
                "usage: shift_runtime_body_solver_export_frame_check "
                "body_solver_export.sbex");
        }

        using namespace shift::runtime::physics;
        const PreparedBodySolverExportFrame frame =
            load_prepared_body_solver_export_frame(argv[1]);
        const PreparedBodySolverExportFrameResult result =
            execute_prepared_body_solver_export_frame(frame);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodySolverExportFrameCheck/1\",\n"
            << "  \"source_function\": \"FUN_007ba570\",\n"
            << "  \"body_count\": "
            << result.body_count << ",\n"
            << "  \"solver_scalar_count\": "
            << result.solver_vector.size() << ",\n"
            << "  \"solver_matrix_double_count\": "
            << result.solver_matrix.size() << ",\n"
            << "  \"max_error\": "
            << std::setprecision(17)
            << result.max_absolute_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_solver_export_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
