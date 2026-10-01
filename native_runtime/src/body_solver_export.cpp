#include "shift_body_solver_export.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

BodySolverExportResult add_body_solver_contributions(
    const std::vector<double>& body_solver_vector,
    const std::vector<double>& body_solver_matrix,
    std::vector<double>& solver_vector_destination,
    std::vector<double>& solver_matrix_destination) {

    if (solver_vector_destination.size() <
        body_solver_vector.size()) {
        throw std::runtime_error(
            "FUN_007ba570 solver vector destination is shorter "
            "than body contribution");
    }
    if (solver_matrix_destination.size() <
        body_solver_matrix.size()) {
        throw std::runtime_error(
            "FUN_007ba570 solver matrix destination is shorter "
            "than body contribution");
    }

    for (std::size_t index = 0;
         index < body_solver_vector.size();
         ++index) {
        solver_vector_destination[index] +=
            body_solver_vector[index];
    }
    for (std::size_t index = 0;
         index < body_solver_matrix.size();
         ++index) {
        solver_matrix_destination[index] +=
            body_solver_matrix[index];
    }

    return {
        body_solver_vector.size(),
        body_solver_matrix.size(),
    };
}

}  // namespace shift::runtime::physics
