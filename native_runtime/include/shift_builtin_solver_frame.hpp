#pragma once

#include "shift_builtin_sparse_solver.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBuiltinSolverFrameFormat =
    "SHIFT.NativeBuiltinSolverFrame/1";
inline constexpr const char* kNativeBuiltinSolverFramePacketFormat =
    "SHIFT.NativeBuiltinSolverFramePacket/1";

struct PreparedBuiltinSolverFrame {
    std::vector<std::vector<double>> matrix;
    std::vector<double> rhs;
    std::vector<std::size_t> reset_nodes;
    std::vector<SparseForwardRecord> forward_records;
    std::vector<SparseReverseRecord> reverse_records;
    std::vector<double> expected_solution;
};

struct PreparedBuiltinSolverFrameResult {
    std::vector<std::size_t> reset_nodes;
    std::vector<std::vector<double>> factorized_matrix;
    std::vector<double> solution;
    double max_absolute_error = 0.0;
};

PreparedBuiltinSolverFrame load_prepared_builtin_solver_frame(
    const std::string& path);

PreparedBuiltinSolverFrameResult
execute_prepared_builtin_solver_frame_with_reset_nodes(
    const PreparedBuiltinSolverFrame& frame,
    const std::vector<std::size_t>& reset_nodes,
    double tolerance = 1e-10);

PreparedBuiltinSolverFrameResult execute_prepared_builtin_solver_frame(
    const PreparedBuiltinSolverFrame& frame,
    double tolerance = 1e-10);

}  // namespace shift::runtime::physics
