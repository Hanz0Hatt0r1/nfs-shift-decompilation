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

void check_builtin_diagonal_reset() {
    using namespace shift::runtime::physics;

    const auto result = apply_builtin_diagonal_reset(
        {
            {1.0, 2.0, 3.0},
            {4.0, 5.0, 6.0},
            {7.0, 8.0, 9.0},
        },
        {10.0, 11.0, 12.0},
        {1u, 1u});

    require(
        result.nodes == std::vector<std::size_t>{1u},
        "diagonal reset did not deduplicate nodes");
    require(result.matrix == std::vector<std::vector<double>>{
                {1.0, 0.0, 3.0},
                {0.0, 1.0, 0.0},
                {7.0, 0.0, 9.0}},
            "diagonal reset matrix mismatch");
    require(result.rhs == std::vector<double>{
                10.0, 0.0, 12.0},
            "diagonal reset RHS mismatch");
}

void check_builtin_diagonal_reset_range() {
    using namespace shift::runtime::physics;

    bool rejected = false;
    try {
        apply_builtin_diagonal_reset(
            {{1.0}},
            {2.0},
            {1u});
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected,
            "out-of-range diagonal reset node was accepted");
}

void check_builtin_solver_frame_with_reset() {
    using namespace shift::runtime::physics;

    const std::vector<std::vector<double>> matrix = {
        {4.0, 1.0, 1.0},
        {1.0, 3.0, 0.0},
        {1.0, 0.0, 2.0},
    };
    const auto graph = build_dense_solver_graph(3);
    const auto frame = execute_builtin_solver_frame(
        matrix,
        {9.0, 7.0, 7.0},
        {1u},
        graph.first,
        graph.second);

    require(frame.reset.nodes ==
                std::vector<std::size_t>{1u},
            "solver frame reset-node mismatch");
    require(nearly_equal(
                frame.reset.matrix[1][1],
                1.0),
            "solver frame reset diagonal mismatch");
    require(nearly_equal(
                frame.solve.solution[0],
                11.0 / 7.0),
            "solver frame x0 mismatch");
    require(nearly_equal(
                frame.solve.solution[1],
                0.0),
            "solver frame x1 mismatch");
    require(nearly_equal(
                frame.solve.solution[2],
                19.0 / 7.0),
            "solver frame x2 mismatch");
}

void check_builtin_solver_frame_without_reset() {
    using namespace shift::runtime::physics;

    const auto graph = build_dense_solver_graph(3);
    const auto frame = execute_builtin_solver_frame(
        {
            {4.0, 1.0, 1.0},
            {1.0, 3.0, 0.0},
            {1.0, 0.0, 2.0},
        },
        {9.0, 7.0, 7.0},
        {},
        graph.first,
        graph.second);

    require(frame.reset.nodes.empty(),
            "empty reset set changed frame reset nodes");
    require(nearly_equal(frame.solve.solution[0], 1.0),
            "unreset solver frame x0 mismatch");
    require(nearly_equal(frame.solve.solution[1], 2.0),
            "unreset solver frame x1 mismatch");
    require(nearly_equal(frame.solve.solution[2], 3.0),
            "unreset solver frame x2 mismatch");
}

}  // namespace

int main() {
    try {
        check_three_by_three();
        check_four_by_four();
        check_bad_graph_cardinality();
        check_zero_pivot();
        check_builtin_diagonal_reset();
        check_builtin_diagonal_reset_range();
        check_builtin_solver_frame_with_reset();
        check_builtin_solver_frame_without_reset();

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBuiltinSparseSolverCheck/1\",\n"
            << "  \"source_function\": "
            << "\"" << shift::runtime::physics::
                kBuiltinSparseSolverSourceFunction << "\",\n"
            << "  \"diagonal_reset_source_function\": "
            << "\"" << shift::runtime::physics::
                kBuiltinDiagonalResetSourceFunction << "\",\n"
            << "  \"builtin_frame_sequence\": \""
            << shift::runtime::physics::
                kBuiltinSolverFrameSequence << "\",\n"
            << "  \"solver_cases\": 4,\n"
            << "  \"diagonal_reset_cases\": 2,\n"
            << "  \"builtin_frame_cases\": 2,\n"
            << "  \"cases\": 8,\n"
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
