#include "shift_post_solve_projection.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::runtime_error(
                "usage: shift_runtime_post_solve_persistence_check "
                "post_solve.sbps steps");
        }

        const int steps = std::stoi(argv[2]);
        if (steps <= 0 || steps > 100000) {
            throw std::runtime_error(
                "persistent post-solve step count out of range");
        }

        using namespace shift::runtime::physics;
        const PreparedPostSolveBodyProjection projection =
            load_prepared_post_solve_body_projection(argv[1]);

        std::vector<BodyAccumulatorState> state =
            projection.bodies;
        double max_delta_error = 0.0;
        for (int step = 0; step < steps; ++step) {
            const auto result =
                execute_post_solve_body_projection_with_state(
                    projection,
                    projection.solver_vector,
                    state);
            state = result.bodies;
            max_delta_error = std::max(
                max_delta_error,
                result.max_delta_error);
        }

        double max_accumulation_error = 0.0;
        for (std::size_t body = 0;
             body < state.size(); ++body) {
            for (std::size_t component = 0;
                 component < 3; ++component) {
                for (int channel = 0;
                     channel < 2; ++channel) {
                    const double initial =
                        channel == 0
                            ? projection.bodies[body]
                                  .angular[component]
                            : projection.bodies[body]
                                  .linear[component];
                    const double one_step =
                        channel == 0
                            ? projection.expected_bodies[body]
                                  .angular[component]
                            : projection.expected_bodies[body]
                                  .linear[component];
                    const double actual =
                        channel == 0
                            ? state[body].angular[component]
                            : state[body].linear[component];
                    const double expected =
                        initial +
                        static_cast<double>(steps) *
                            (one_step - initial);
                    max_accumulation_error = std::max(
                        max_accumulation_error,
                        std::abs(actual - expected));
                }
            }
        }

        if (max_accumulation_error > 1e-10 ||
            max_delta_error > 1e-10) {
            throw std::runtime_error(
                "persistent post-solve accumulation mismatch");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativePostSolvePersistenceCheck/1\",\n"
            << "  \"source_function\": "
            << "\"FUN_007b4110\",\n"
            << "  \"steps\": " << steps << ",\n"
            << "  \"body_count\": "
            << state.size() << ",\n"
            << "  \"max_delta_error\": "
            << std::setprecision(17)
            << max_delta_error << ",\n"
            << "  \"max_accumulation_error\": "
            << max_accumulation_error << ",\n"
            << "  \"persistent_vehicle_state_applied\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_post_solve_persistence_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
