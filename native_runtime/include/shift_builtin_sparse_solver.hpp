#pragma once

#include <cstddef>
#include <utility>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kBuiltinSparseSolverFormat =
    "SHIFT.NativeBuiltinSparseSolver/1";
inline constexpr const char* kBuiltinSparseSolverSourceFunction =
    "FUN_007b0f20";
inline constexpr const char* kBuiltinDiagonalResetFormat =
    "SHIFT.NativeBuiltinDiagonalReset/1";
inline constexpr const char* kBuiltinDiagonalResetSourceFunction =
    "FUN_007b2210";
inline constexpr const char* kBuiltinSolverFrameFormat =
    "SHIFT.NativeBuiltinSolverFrame/1";
inline constexpr const char* kBuiltinSolverFrameSequence =
    "FUN_007b2210 -> FUN_007b0f20";

struct SparseForwardItem {
    std::size_t node = 0;
    std::vector<std::size_t> dependencies;
};

struct SparseForwardRecord {
    std::vector<SparseForwardItem> items;
};

struct SparseReverseRecord {
    std::size_t node = 0;
    std::vector<std::size_t> dependencies;
};

struct BuiltinSparseSolveResult {
    std::vector<std::vector<double>> factorized_matrix;
    std::vector<double> solution;
};

struct BuiltinDiagonalResetResult {
    std::vector<std::vector<double>> matrix;
    std::vector<double> rhs;
    std::vector<std::size_t> nodes;
};

struct BuiltinSolverFrameResult {
    BuiltinDiagonalResetResult reset;
    BuiltinSparseSolveResult solve;
};

BuiltinDiagonalResetResult apply_builtin_diagonal_reset(
    const std::vector<std::vector<double>>& matrix,
    const std::vector<double>& rhs,
    const std::vector<std::size_t>& nodes);

BuiltinSolverFrameResult execute_builtin_solver_frame(
    const std::vector<std::vector<double>>& matrix,
    const std::vector<double>& rhs,
    const std::vector<std::size_t>& reset_nodes,
    const std::vector<SparseForwardRecord>& forward_records,
    const std::vector<SparseReverseRecord>& reverse_records);

BuiltinSparseSolveResult solve_builtin_sparse(
    const std::vector<std::vector<double>>& matrix,
    const std::vector<double>& rhs,
    const std::vector<SparseForwardRecord>& forward_records,
    const std::vector<SparseReverseRecord>& reverse_records);

std::pair<
    std::vector<SparseForwardRecord>,
    std::vector<SparseReverseRecord>>
build_dense_solver_graph(std::size_t scalar_count);

}  // namespace shift::runtime::physics
