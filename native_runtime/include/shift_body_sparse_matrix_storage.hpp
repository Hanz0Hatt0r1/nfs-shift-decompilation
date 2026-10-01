#pragma once

#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

struct BodySparseMatrixStorage {
    std::size_t scalar_count = 0;
    std::size_t matrix_double_count = 0;
    std::vector<std::size_t> row_indices;
    std::vector<std::size_t> row_pointer_byte_offsets;
    std::vector<double> matrix_pool;
    std::size_t lower_domain_cell_count = 0;
    std::size_t nonzero_written_cell_count = 0;
};

BodySparseMatrixStorage materialize_fun_007bb8d0_sparse_rows(
    const std::vector<double>& lower_matrix,
    std::size_t scalar_count,
    const std::vector<std::size_t>& row_indices,
    std::size_t matrix_double_count);

double read_fun_007bb8d0_sparse_cell(
    const BodySparseMatrixStorage& storage,
    std::size_t row,
    std::size_t column);

}  // namespace shift::runtime::physics
