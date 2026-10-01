#include "shift_post_solve_projection.hpp"

#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error(
                "usage: shift_runtime_post_solve_projection_check "
                "post_solve.sbps");
        }

        using namespace shift::runtime::physics;
        const PreparedPostSolveBodyProjection projection =
            load_prepared_post_solve_body_projection(argv[1]);
        const PostSolveBodyProjectionResult result =
            execute_prepared_post_solve_body_projection(projection);

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativePostSolveBodyProjectionCheck/1\",\n"
            << "  \"projection_format\": \""
            << kNativePostSolveProjectionFormat << "\",\n"
            << "  \"packet_format\": \""
            << kNativePostSolveProjectionPacketFormat << "\",\n"
            << "  \"source_function\": \""
            << kPostSolveSourceFunction << "\",\n"
            << "  \"body_count\": " << result.bodies.size() << ",\n"
            << "  \"max_absolute_oracle_error\": "
            << std::setprecision(17)
            << result.max_absolute_error << ",\n"
            << "  \"fixed_step_runtime_integration\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_post_solve_projection_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
