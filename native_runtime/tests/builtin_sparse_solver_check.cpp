#include "shift_builtin_sparse_solver.hpp"

#include <cmath>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

bool nearly_equal(
    double lhs,
    double rhs,
    double tolerance = 1e-12) {
    return std::abs(lhs - rhs) <= tolerance;
}

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void check_three_by_three() {
    using namespace shift::runtime::physics;

    const std::vector<std::vector<double>> matrix = {
        {4.0, 1.0, 1.0},
        {1.0, 3.0, 0.0},
        {1.0, 0.0, 2.0},
    };
    const std::vector<double> rhs = {
        9.0, 7.0, 7.0
    };
    const auto graph = build_dense_solver_graph(3);
    const auto result = solve_builtin_sparse(
        matrix,
        rhs,
        graph.first,
        graph.second);

    require(result.solution.size() == 3u,
            "3x3 solution size mismatch");
    require(nearly_equal(result.solution[0], 1.0),
            "3x3 x0 mismatch");
    require(nearly_equal(result.solution[1], 2.0),
            "3x3 x1 mismatch");
    require(nearly_equal(result.solution[2], 3.0),
            "3x3 x2 mismatch");
    require(nearly_equal(
                result.factorized_matrix[0][1],
                0.25),
            "3x3 factor A01 mismatch");
    require(nearly_equal(
                result.factorized_matrix[1][2],
                -0.09090909090909091),
            "3x3 factor A12 mismatch");
}

void check_four_by_four() {
    using namespace shift::runtime::physics;

    const std::vector<std::vector<double>> matrix = {
        {6.0, 1.0, 2.0, 0.0},
        {1.0, 5.0, 0.5, 1.0},
        {2.0, 0.5, 7.0, 1.5},
        {0.0, 1.0, 1.5, 4.0},
    };
    const std::vector<double> rhs = {
        5.0, -5.75, 9.0, 10.75
    };
    const std::vector<double> expected = {
        1.0, -2.0, 0.5, 3.0
    };

    const auto graph = build_dense_solver_graph(4);
    const auto result = solve_builtin_sparse(
        matrix,
        rhs,
        graph.first,
        graph.second);

    require(result.solution.size() == expected.size(),
            "4x4 solution size mismatch");
    for (std::size_t i = 0;
         i < expected.size();
         ++i) {
        require(nearly_equal(
                    result.solution[i],
                    expected[i]),
                "4x4 solution mismatch");
    }
}

void check_bad_graph_cardinality() {
    using namespace shift::runtime::physics;

    bool rejected = false;
    try {
        solve_builtin_sparse(
            {{1.0}},
            {1.0},
            {},
            {{0u, {}}});
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected,
            "bad graph cardinality was accepted");
}

void check_zero_pivot() {
    using namespace shift::runtime::physics;

    const auto graph = build_dense_solver_graph(1);
    bool rejected = false;
    try {
        solve_builtin_sparse(
            {{0.0}},
            {1.0},
            graph.first,
            graph.second);
    } catch (const std::domain_error&) {
        rejected = true;
    }
    require(rejected, "zero pivot was accepted");
}

}  // namespace

int main() {
    try {
        check_three_by_three();
        check_four_by_four();
        check_bad_graph_cardinality();
        check_zero_pivot();

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBuiltinSparseSolverCheck/1\",\n"
            << "  \"source_function\": "
            << "\"" << shift::runtime::physics::
                kBuiltinSparseSolverSourceFunction << "\",\n"
            << "  \"cases\": 4,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_builtin_solver_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
