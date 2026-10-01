#include "shift_body_sparse_matrix_storage.hpp"

#include <cmath>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    try {
        using namespace shift::runtime::physics;

        const std::vector<double> lower = {
            19.5, 0.0, 0.0, 0.0, 0.0, 0.0,
            -3.75, 15.5, 0.0, 0.0, 0.0, 0.0,
            -5.25, -8.75, 9.5, 0.0, 0.0, 0.0,
            -0.5, 1.0, -0.5, 14.0, 0.0, 0.0,
            2.5, -5.0, 2.5, 32.0, 77.0, 0.0,
            -3.0, 24.0, -13.0, 6.0, 3.0, 41.0,
        };
        const std::vector<std::size_t> row_indices = {
            18u, 0u, 30u, 6u, 24u, 12u,
        };
        const auto storage =
            materialize_fun_007bb8d0_sparse_rows(
                lower,
                6u,
                row_indices,
                36u);

        if (storage.row_pointer_byte_offsets !=
            std::vector<std::size_t>{
                144u, 0u, 240u, 48u, 192u, 96u,
            }) {
            throw std::runtime_error(
                "BODY row-pointer byte offsets mismatch");
        }
        if (storage.lower_domain_cell_count != 21u ||
            storage.nonzero_written_cell_count != 21u) {
            throw std::runtime_error(
                "BODY sparse write counts mismatch");
        }

        double max_absolute_error = 0.0;
        for (std::size_t row = 0; row < 6u; ++row) {
            for (std::size_t column = 0;
                 column < 6u;
                 ++column) {
                const double actual =
                    read_fun_007bb8d0_sparse_cell(
                        storage,
                        row,
                        column);
                const double expected =
                    column <= row
                        ? lower[row * 6u + column]
                        : 0.0;
                max_absolute_error = std::max(
                    max_absolute_error,
                    std::abs(actual - expected));
                if (actual != expected) {
                    throw std::runtime_error(
                        "BODY sparse row mapping mismatch");
                }
            }
        }

        bool alias_rejected = false;
        try {
            (void)materialize_fun_007bb8d0_sparse_rows(
                lower,
                6u,
                {0u, 0u, 12u, 18u, 24u, 30u},
                36u);
        } catch (const std::invalid_argument&) {
            alias_rejected = true;
        }
        if (!alias_rejected) {
            throw std::runtime_error(
                "aliased BODY row pointers were accepted");
        }

        bool range_rejected = false;
        try {
            (void)materialize_fun_007bb8d0_sparse_rows(
                lower,
                6u,
                {0u, 6u, 12u, 18u, 24u, 31u},
                36u);
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "out-of-range BODY row pointer was accepted");
        }

        bool upper_rejected = false;
        try {
            auto invalid = lower;
            invalid[1u] = 1.0;
            (void)materialize_fun_007bb8d0_sparse_rows(
                invalid,
                6u,
                row_indices,
                36u);
        } catch (const std::invalid_argument&) {
            upper_rejected = true;
        }
        if (!upper_rejected) {
            throw std::runtime_error(
                "upper-triangle BODY write was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodySparseMatrixStorageCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bb8d0\",\n"
            << "  \"matrix_base\": \"BODY+0x154\",\n"
            << "  \"row_pointer_table\": \"BODY+0x158\",\n"
            << "  \"row_index_vector\": \"BODY+0x15c\",\n"
            << "  \"scalar_count\": 6,\n"
            << "  \"matrix_double_count\": 36,\n"
            << "  \"lower_domain_cell_count\": 21,\n"
            << "  \"nonzero_written_cell_count\": 21,\n"
            << "  \"noncanonical_row_order_verified\": true,\n"
            << "  \"alias_rejected\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"upper_triangle_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << max_absolute_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_sparse_matrix_storage_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
