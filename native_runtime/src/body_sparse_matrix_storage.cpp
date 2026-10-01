#include "shift_body_sparse_matrix_storage.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::physics {
namespace {

void require_finite(
    const std::vector<double>& values,
    const char* label) {

    for (double value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                std::string(label) +
                " contains non-finite value");
        }
    }
}

}  // namespace

BodySparseMatrixStorage materialize_fun_007bb8d0_sparse_rows(
    const std::vector<double>& lower_matrix,
    std::size_t scalar_count,
    const std::vector<std::size_t>& row_indices,
    std::size_t matrix_double_count) {

    require_finite(lower_matrix, "BODY lower matrix");
    if (scalar_count == 0 ||
        lower_matrix.size() != scalar_count * scalar_count) {
        throw std::invalid_argument(
            "BODY lower matrix shape is invalid");
    }
    if (row_indices.size() != scalar_count) {
        throw std::invalid_argument(
            "BODY row-index count must equal scalar_count");
    }
    if (matrix_double_count == 0) {
        throw std::invalid_argument(
            "BODY matrix pool must be non-empty");
    }

    // Phase 624 promises source-faithful lower-triangle writes only.
    for (std::size_t row = 0; row < scalar_count; ++row) {
        for (std::size_t column = row + 1;
             column < scalar_count;
             ++column) {
            if (lower_matrix[
                    row * scalar_count + column] != 0.0) {
                throw std::invalid_argument(
                    "BODY matrix contains upper-triangle write");
            }
        }
    }

    std::vector<std::pair<std::size_t, std::size_t>> spans;
    spans.reserve(scalar_count);
    for (std::size_t row = 0; row < scalar_count; ++row) {
        const std::size_t offset = row_indices[row];
        if (offset > matrix_double_count ||
            scalar_count > matrix_double_count - offset) {
            throw std::out_of_range(
                "BODY row pointer span exceeds matrix pool");
        }
        spans.push_back({
            offset,
            offset + scalar_count,
        });
    }
    std::sort(spans.begin(), spans.end());
    for (std::size_t i = 1; i < spans.size(); ++i) {
        if (spans[i].first < spans[i - 1].second) {
            throw std::invalid_argument(
                "BODY row pointer spans alias");
        }
    }

    BodySparseMatrixStorage result{};
    result.scalar_count = scalar_count;
    result.matrix_double_count = matrix_double_count;
    result.row_indices = row_indices;
    result.row_pointer_byte_offsets.reserve(
        scalar_count);
    result.matrix_pool.assign(
        matrix_double_count,
        0.0);
    result.lower_domain_cell_count =
        scalar_count * (scalar_count + 1u) / 2u;

    for (std::size_t row = 0; row < scalar_count; ++row) {
        const std::size_t row_offset = row_indices[row];
        result.row_pointer_byte_offsets.push_back(
            row_offset * sizeof(double));
        for (std::size_t column = 0;
             column <= row;
             ++column) {
            const double value =
                lower_matrix[
                    row * scalar_count + column];
            result.matrix_pool[
                row_offset + column] += value;
            if (value != 0.0) {
                ++result.nonzero_written_cell_count;
            }
        }
    }

    return result;
}

double read_fun_007bb8d0_sparse_cell(
    const BodySparseMatrixStorage& storage,
    std::size_t row,
    std::size_t column) {

    if (row >= storage.scalar_count ||
        column >= storage.scalar_count) {
        throw std::out_of_range(
            "BODY sparse matrix cell is outside scalar domain");
    }
    if (storage.row_indices.size() !=
        storage.scalar_count) {
        throw std::invalid_argument(
            "BODY sparse storage row-index count is invalid");
    }
    const std::size_t offset =
        storage.row_indices[row];
    if (offset > storage.matrix_pool.size() ||
        column >= storage.matrix_pool.size() - offset) {
        throw std::out_of_range(
            "BODY sparse matrix cell exceeds pool");
    }
    return storage.matrix_pool[offset + column];
}

}  // namespace shift::runtime::physics
