#pragma once

#include "shift_body_solver_export_frame.hpp"
#include "shift_builtin_solver_frame.hpp"

#include <cstddef>

namespace shift::runtime::physics {

struct BodyExportSolverFrameJoinResult {
    std::size_t scalar_count = 0;
    std::size_t matrix_double_count = 0;
    double max_rhs_join_error = 0.0;
    double max_matrix_join_error = 0.0;
    double max_solver_oracle_error = 0.0;
};

BodyExportSolverFrameJoinResult verify_body_export_matches_builtin_solver_frame(
    const PreparedBodySolverExportFrame& export_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance = 1e-12);

BodyExportSolverFrameJoinResult join_body_export_to_builtin_solver_frame(
    const PreparedBodySolverExportFrame& export_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance = 1e-12);

}  // namespace shift::runtime::physics
