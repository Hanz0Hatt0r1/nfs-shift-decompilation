#include "shift_builtin_solver_frame.hpp"
#include "shift_builtin_sparse_solver.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error(
                "usage: shift_runtime_builtin_solver_frame_check "
                "solver_frame.sbfr");
        }

        using namespace shift::runtime::physics;
        const PreparedBuiltinSolverFrame frame =
            load_prepared_builtin_solver_frame(argv[1]);
        const PreparedBuiltinSolverFrameResult result =
            execute_prepared_builtin_solver_frame(frame);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBuiltinSolverFrameCheck/1\",\n"
            << "  \"frame_format\": "
            << "\"" << kNativeBuiltinSolverFrameFormat << "\",\n"
            << "  \"packet_format\": "
            << "\"" << kNativeBuiltinSolverFramePacketFormat << "\",\n"
            << "  \"reset_source_function\": "
            << "\"" << kBuiltinDiagonalResetSourceFunction << "\",\n"
            << "  \"solve_source_function\": "
            << "\"" << kBuiltinSparseSolverSourceFunction << "\",\n"
            << "  \"scalar_count\": "
            << result.solution.size() << ",\n"
            << "  \"reset_node_count\": "
            << result.reset_nodes.size() << ",\n"
            << "  \"provider_absent_proven\": true,\n"
            << "  \"matrix_rhs_ready\": true,\n"
            << "  \"reset_selection_ready\": true,\n"
            << "  \"sparse_graph_ready\": true,\n"
            << "  \"max_absolute_oracle_error\": "
            << std::setprecision(17)
            << result.max_absolute_error << ",\n"
            << "  \"fixed_step_runtime_integration\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_builtin_solver_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
