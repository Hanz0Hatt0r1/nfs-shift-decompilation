#pragma once

#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kBodySolverExportSourceFunction =
    "FUN_007ba570";

struct BodySolverExportResult {
    std::size_t solver_vector_count = 0;
    std::size_t solver_matrix_count = 0;
};

BodySolverExportResult add_body_solver_contributions(
    const std::vector<double>& body_solver_vector,
    const std::vector<double>& body_solver_matrix,
    std::vector<double>& solver_vector_destination,
    std::vector<double>& solver_matrix_destination);

}  // namespace shift::runtime::physics
