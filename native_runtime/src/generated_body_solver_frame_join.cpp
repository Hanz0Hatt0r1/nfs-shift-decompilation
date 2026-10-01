#include "shift_generated_body_solver_frame_join.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

double compare_value(
    double actual,
    double expected,
    double tolerance,
    const char* label) {

    if (!std::isfinite(actual) ||
        !std::isfinite(expected)) {
        throw std::runtime_error(
            std::string(label) +
            " contains non-finite value");
    }
    const double error =
        std::abs(actual - expected);
    const double limit =
        tolerance *
        std::max(1.0, std::abs(expected));
    if (error > limit) {
        throw std::runtime_error(
            std::string(label) +
            " join mismatch");
    }
    return error;
}

}  // namespace

GeneratedBodySolverFrameJoinResult
verify_generated_body_constraints_match_builtin_solver_frame(
    const PreparedGeneratedBodyConstraintFrame& generated_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance) {

    if (!std::isfinite(tolerance) ||
        tolerance <= 0.0) {
        throw std::invalid_argument(
            "generated BODY/solver join tolerance must be finite and positive");
    }

    const auto generated =
        execute_prepared_generated_body_constraint_frame(
            generated_frame);

    const std::size_t n =
        generated_frame.scalar_count;
    if (n == 0 ||
        solver_frame.rhs.size() != n ||
        solver_frame.matrix.size() != n) {
        throw std::runtime_error(
            "generated BODY/solver scalar cardinality mismatch");
    }
    if (generated.solver_vector.size() != n ||
        generated.solver_matrix.size() != n * n) {
        throw std::runtime_error(
            "generated BODY global destination shape mismatch");
    }
    for (const auto& row : solver_frame.matrix) {
        if (row.size() != n) {
            throw std::runtime_error(
                "builtin solver-frame matrix is not square");
        }
    }

    double max_rhs_error = 0.0;
    for (std::size_t index = 0;
         index < n;
         ++index) {
        max_rhs_error = std::max(
            max_rhs_error,
            compare_value(
                generated.solver_vector[index],
                solver_frame.rhs[index],
                tolerance,
                "generated BODY/RHS"));
    }

    double max_matrix_error = 0.0;
    for (std::size_t row = 0;
         row < n;
         ++row) {
        for (std::size_t column = 0;
             column < n;
             ++column) {
            const std::size_t offset =
                row * n + column;
            max_matrix_error = std::max(
                max_matrix_error,
                compare_value(
                    generated.solver_matrix[offset],
                    solver_frame.matrix[row][column],
                    tolerance,
                    "generated BODY/matrix"));
        }
    }

    return {
        n,
        n * n,
        generated.body_count,
        max_rhs_error,
        max_matrix_error,
        0.0,
    };
}

GeneratedBodySolverFrameJoinResult
join_generated_body_constraints_to_builtin_solver_frame(
    const PreparedGeneratedBodyConstraintFrame& generated_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance) {

    auto result =
        verify_generated_body_constraints_match_builtin_solver_frame(
            generated_frame,
            solver_frame,
            tolerance);
    const auto solver_result =
        execute_prepared_builtin_solver_frame(
            solver_frame,
            tolerance);
    result.max_solver_oracle_error =
        solver_result.max_absolute_error;
    return result;
}

}  // namespace shift::runtime::physics
