#include "shift_generated_body_solver_export.hpp"

#include <stdexcept>
#include <vector>

namespace shift::runtime::physics {

std::vector<std::size_t> canonical_builtin_body_row_indices(
    std::size_t scalar_count) {

    std::vector<std::size_t> result;
    result.reserve(scalar_count);
    for (std::size_t row = 0; row < scalar_count; ++row) {
        result.push_back(row * scalar_count);
    }
    return result;
}

GeneratedBodySolverExportResult
generate_and_export_fun_007bc680_body(
    const GeneratedBodySolverExportInput& input) {

    if (input.provider_present) {
        throw std::invalid_argument(
            "generated BODY export does not admit provider-present row storage");
    }

    const std::size_t scalar_count =
        input.constraints.scalar_count;
    if (scalar_count == 0) {
        throw std::invalid_argument(
            "generated BODY export scalar_count must be non-zero");
    }

    const std::size_t expected_matrix_count =
        scalar_count * scalar_count;
    if (input.matrix_double_count != expected_matrix_count) {
        throw std::invalid_argument(
            "generated BODY export builtin matrix count must equal N squared");
    }

    const auto canonical =
        canonical_builtin_body_row_indices(
            scalar_count);
    if (input.row_indices != canonical) {
        throw std::invalid_argument(
            "generated BODY export requires canonical builtin row indices");
    }

    GeneratedBodySolverExportResult result{};
    result.canonical_builtin_row_layout = true;
    result.assembly =
        assemble_fun_007bc680_body_constraints(
            input.constraints);
    result.sparse_storage =
        materialize_fun_007bb8d0_sparse_rows(
            result.assembly.lower_matrix,
            scalar_count,
            input.row_indices,
            input.matrix_double_count);

    result.contribution.body_index =
        input.body_index;
    result.contribution.solver_vector =
        result.assembly.solver_vector;
    result.contribution.solver_matrix =
        result.sparse_storage.matrix_pool;

    result.exported_solver_vector.assign(
        scalar_count,
        0.0);
    result.exported_solver_matrix.assign(
        input.matrix_double_count,
        0.0);
    result.export_result =
        add_body_solver_contributions(
            result.contribution.solver_vector,
            result.contribution.solver_matrix,
            result.exported_solver_vector,
            result.exported_solver_matrix);

    if (result.export_result.solver_vector_count !=
            scalar_count ||
        result.export_result.solver_matrix_count !=
            input.matrix_double_count) {
        throw std::runtime_error(
            "FUN_007ba570 generated BODY export count mismatch");
    }
    return result;
}

}  // namespace shift::runtime::physics
