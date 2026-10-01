#include "shift_body_export_solver_join.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

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
            std::string(label) + " contains non-finite value");
    }
    const double error = std::abs(actual - expected);
    const double limit =
        tolerance * std::max(1.0, std::abs(expected));
    if (error > limit) {
        throw std::runtime_error(
            std::string(label) + " join mismatch");
    }
    return error;
}

}  // namespace

BodyExportSolverFrameJoinResult join_body_export_to_builtin_solver_frame(
    const PreparedBodySolverExportFrame& export_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance) {

    if (!std::isfinite(tolerance) ||
        tolerance <= 0.0) {
        throw std::invalid_argument(
            "BODY export/solver join tolerance must be finite and positive");
    }

    const auto exported =
        execute_prepared_body_solver_export_frame(
            export_frame,
            tolerance);

    const std::size_t n = export_frame.scalar_count;
    if (n == 0 ||
        solver_frame.rhs.size() != n ||
        solver_frame.matrix.size() != n) {
        throw std::runtime_error(
            "BODY export/solver scalar cardinality mismatch");
    }
    if (exported.solver_vector.size() != n ||
        exported.solver_matrix.size() != n * n) {
        throw std::runtime_error(
            "BODY export global destination shape mismatch");
    }
    for (const auto& row : solver_frame.matrix) {
        if (row.size() != n) {
            throw std::runtime_error(
                "builtin solver-frame matrix is not square");
        }
    }

    double max_rhs_error = 0.0;
    for (std::size_t index = 0; index < n; ++index) {
        max_rhs_error = std::max(
            max_rhs_error,
            compare_value(
                exported.solver_vector[index],
                solver_frame.rhs[index],
                tolerance,
                "BODY export/RHS"));
    }

    double max_matrix_error = 0.0;
    for (std::size_t row = 0; row < n; ++row) {
        for (std::size_t column = 0;
             column < n;
             ++column) {
            const std::size_t offset =
                row * n + column;
            max_matrix_error = std::max(
                max_matrix_error,
                compare_value(
                    exported.solver_matrix[offset],
                    solver_frame.matrix[row][column],
                    tolerance,
                    "BODY export/matrix"));
        }
    }

    const auto solver_result =
        execute_prepared_builtin_solver_frame(
            solver_frame,
            tolerance);

    return {
        n,
        n * n,
        max_rhs_error,
        max_matrix_error,
        solver_result.max_absolute_error,
    };
}

}  // namespace shift::runtime::physics
