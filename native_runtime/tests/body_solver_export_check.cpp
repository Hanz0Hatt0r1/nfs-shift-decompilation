#include "shift_body_solver_export.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

double max_error(
    const std::vector<double>& actual,
    const std::vector<double>& expected) {

    if (actual.size() != expected.size()) {
        throw std::runtime_error("vector size mismatch");
    }
    double error = 0.0;
    for (std::size_t index = 0;
         index < actual.size();
         ++index) {
        error = std::max(
            error,
            std::abs(actual[index] - expected[index]));
    }
    return error;
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        std::vector<double> solver_vector{
            10.0, 20.0, 30.0, 40.0
        };
        std::vector<double> solver_matrix{
            1.0, 2.0, 3.0
        };

        const auto first =
            add_body_solver_contributions(
                {1.0, 2.5, -3.0},
                {4.0, -5.0},
                solver_vector,
                solver_matrix);

        double error = 0.0;
        error = std::max(
            error,
            max_error(
                solver_vector,
                {11.0, 22.5, 27.0, 40.0}));
        error = std::max(
            error,
            max_error(
                solver_matrix,
                {5.0, -3.0, 3.0}));

        const auto second =
            add_body_solver_contributions(
                {-1.0, 0.5, 3.0},
                {1.0, 2.0, -3.0},
                solver_vector,
                solver_matrix);

        error = std::max(
            error,
            max_error(
                solver_vector,
                {10.0, 23.0, 30.0, 40.0}));
        error = std::max(
            error,
            max_error(
                solver_matrix,
                {6.0, -1.0, 0.0}));

        bool short_destination_rejected = false;
        try {
            std::vector<double> short_vector{0.0};
            std::vector<double> matrix{0.0};
            add_body_solver_contributions(
                {1.0, 2.0},
                {1.0},
                short_vector,
                matrix);
        } catch (const std::runtime_error&) {
            short_destination_rejected = true;
        }
        if (!short_destination_rejected) {
            throw std::runtime_error(
                "short solver destination was accepted");
        }
        if (error > 1e-12) {
            throw std::runtime_error(
                "FUN_007ba570 additive export parity mismatch");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodySolverExportCheck/1\",\n"
            << "  \"source_function\": "
            << "\"" << kBodySolverExportSourceFunction << "\",\n"
            << "  \"first_vector_count\": "
            << first.solver_vector_count << ",\n"
            << "  \"first_matrix_count\": "
            << first.solver_matrix_count << ",\n"
            << "  \"second_vector_count\": "
            << second.solver_vector_count << ",\n"
            << "  \"second_matrix_count\": "
            << second.solver_matrix_count << ",\n"
            << "  \"max_error\": "
            << std::setprecision(17) << error << ",\n"
            << "  \"short_destination_rejected\": true,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_solver_export_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
