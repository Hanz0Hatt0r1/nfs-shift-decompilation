#pragma once

#include "shift_builtin_solver_frame.hpp"
#include "shift_generated_body_constraint_frame.hpp"

#include <cstddef>

namespace shift::runtime::physics {

struct GeneratedBodySolverFrameJoinResult {
    std::size_t scalar_count = 0;
    std::size_t matrix_double_count = 0;
    std::size_t body_count = 0;
    double max_rhs_join_error = 0.0;
    double max_matrix_join_error = 0.0;
    double max_solver_oracle_error = 0.0;
};

GeneratedBodySolverFrameJoinResult
verify_generated_body_constraints_match_builtin_solver_frame(
    const PreparedGeneratedBodyConstraintFrame& generated_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance = 1e-12);

GeneratedBodySolverFrameJoinResult
join_generated_body_constraints_to_builtin_solver_frame(
    const PreparedGeneratedBodyConstraintFrame& generated_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance = 1e-12);

}  // namespace shift::runtime::physics
