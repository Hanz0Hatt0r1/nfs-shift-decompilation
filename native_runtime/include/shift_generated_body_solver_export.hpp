#pragma once

#include "shift_body_constraint_assembly.hpp"
#include "shift_body_solver_export.hpp"
#include "shift_body_solver_export_frame.hpp"
#include "shift_body_sparse_matrix_storage.hpp"

#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

struct GeneratedBodySolverExportInput {
    std::size_t body_index = 0;
    BodyConstraintAssemblyInput constraints{};
    std::vector<std::size_t> row_indices;
    std::size_t matrix_double_count = 0;
    bool provider_present = false;
};

struct GeneratedBodySolverExportResult {
    BodyConstraintAssemblyResult assembly{};
    BodySparseMatrixStorage sparse_storage{};
    PreparedBodySolverContribution contribution{};
    BodySolverExportResult export_result{};
    std::vector<double> exported_solver_vector;
    std::vector<double> exported_solver_matrix;
    bool canonical_builtin_row_layout = false;
};

std::vector<std::size_t> canonical_builtin_body_row_indices(
    std::size_t scalar_count);

GeneratedBodySolverExportResult
generate_and_export_fun_007bc680_body(
    const GeneratedBodySolverExportInput& input);

}  // namespace shift::runtime::physics
