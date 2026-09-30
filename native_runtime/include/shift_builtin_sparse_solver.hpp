#pragma once

#include <cstddef>
#include <utility>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kBuiltinSparseSolverFormat =
    "SHIFT.NativeBuiltinSparseSolver/1";
inline constexpr const char* kBuiltinSparseSolverSourceFunction =
    "FUN_007b0f20";

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
