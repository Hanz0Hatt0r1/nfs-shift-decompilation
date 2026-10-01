#include "shift_builtin_solver_frame.hpp"
#include "shift_post_solve_projection.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::runtime_error(
                "usage: shift_runtime_solver_post_solve_join_check "
                "solver_frame.sbfr post_solve.sbps");
        }

        using namespace shift::runtime::physics;
        const PreparedBuiltinSolverFrame solver_frame =
            load_prepared_builtin_solver_frame(argv[1]);
        const PreparedPostSolveBodyProjection projection =
            load_prepared_post_solve_body_projection(argv[2]);

        const PreparedBuiltinSolverFrameResult solver_result =
            execute_prepared_builtin_solver_frame(solver_frame);
        const PostSolveBodyProjectionResult projection_result =
            execute_post_solve_body_projection_with_solution(
                projection,
                solver_result.solution);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeSolverPostSolveJoinCheck/1\",\n"
            << "  \"solver_scalar_count\": "
            << solver_result.solution.size() << ",\n"
            << "  \"body_count\": "
            << projection_result.bodies.size() << ",\n"
            << "  \"max_solver_join_error\": "
            << std::setprecision(17)
            << projection_result.max_solver_vector_join_error
            << ",\n"
            << "  \"max_body_oracle_error\": "
            << projection_result.max_absolute_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_solver_post_solve_join_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
