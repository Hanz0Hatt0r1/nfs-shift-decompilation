#include "shift_builtin_sparse_solver.hpp"

#include <cstddef>
#include <stdexcept>
#include <utility>
#include <vector>

namespace shift::runtime::physics {

BuiltinSparseSolveResult solve_builtin_sparse(
    const std::vector<std::vector<double>>& matrix,
    const std::vector<double>& rhs,
    const std::vector<SparseForwardRecord>& forward_records,
    const std::vector<SparseReverseRecord>& reverse_records) {

    const std::size_t n = matrix.size();
    for (const auto& row : matrix) {
        if (row.size() != n) {
            throw std::invalid_argument("matrix must be square");
        }
    }
    if (rhs.size() != n) {
        throw std::invalid_argument(
            "rhs length must match matrix dimension");
    }
    if (forward_records.size() != n + 1u) {
        throw std::invalid_argument(
            "forward_records must contain n+1 records");
    }
    if (reverse_records.size() != n) {
        throw std::invalid_argument(
            "reverse_records must contain n records");
    }

    std::vector<std::vector<double>> a = matrix;
    std::vector<double> b = rhs;

    const auto& terminal_items = forward_records[n].items;
    if (terminal_items.size() != n) {
        throw std::invalid_argument(
            "terminal forward record must contain one item per scalar row");
    }

    for (std::size_t i = 0; i < n; ++i) {
        const auto& pivot_items = forward_records[i].items;
        if (pivot_items.empty()) {
            throw std::invalid_argument(
                "forward record has no pivot item");
        }

        for (const std::size_t k :
             pivot_items.front().dependencies) {
            if (k >= i) {
                throw std::invalid_argument(
                    "invalid pivot dependency");
            }
            a[i][i] -= a[k][i] * a[i][k];
        }

        const double diagonal = a[i][i];
        if (diagonal == 0.0) {
            throw std::domain_error("zero pivot");
        }
        const double inv_diagonal = 1.0 / diagonal;

        for (std::size_t item_index = 1;
             item_index < pivot_items.size();
             ++item_index) {
            const auto& item = pivot_items[item_index];
            const std::size_t j = item.node;
            if (j <= i || j >= n) {
                throw std::invalid_argument(
                    "invalid forward target");
            }
            for (const std::size_t k : item.dependencies) {
                if (k >= i) {
                    throw std::invalid_argument(
                        "invalid row dependency");
                }
                a[j][i] -= a[k][i] * a[j][k];
            }
            a[i][j] = a[j][i] * inv_diagonal;
        }

        const auto& terminal = terminal_items[i];
        for (const std::size_t k : terminal.dependencies) {
            if (k >= i) {
                throw std::invalid_argument(
                    "invalid RHS dependency");
            }
            b[i] -= a[i][k] * b[k];
        }
        b[i] *= inv_diagonal;
    }

    if (n >= 2u) {
        for (std::ptrdiff_t signed_i =
                 static_cast<std::ptrdiff_t>(n) - 2;
             signed_i >= 0;
             --signed_i) {
            const std::size_t i =
                static_cast<std::size_t>(signed_i);
            const auto& reverse = reverse_records[i];
            for (const std::size_t k :
                 reverse.dependencies) {
                if (k <= i || k >= n) {
                    throw std::invalid_argument(
                        "invalid reverse dependency");
                }
                b[i] -= a[i][k] * b[k];
            }
        }
    }

    return {
        std::move(a),
        std::move(b),
    };
}

std::pair<
    std::vector<SparseForwardRecord>,
    std::vector<SparseReverseRecord>>
build_dense_solver_graph(std::size_t scalar_count) {
    if (scalar_count == 0u) {
        throw std::invalid_argument(
            "scalar_count must be positive");
    }

    std::vector<SparseForwardRecord> forward;
    forward.reserve(scalar_count + 1u);

    for (std::size_t i = 0; i < scalar_count; ++i) {
        SparseForwardRecord record{};

        SparseForwardItem pivot{};
        pivot.node = i;
        pivot.dependencies.reserve(i);
        for (std::size_t k = 0; k < i; ++k) {
            pivot.dependencies.push_back(k);
        }
        record.items.push_back(std::move(pivot));

        for (std::size_t j = i + 1u;
             j < scalar_count;
             ++j) {
            SparseForwardItem item{};
            item.node = j;
            item.dependencies.reserve(i);
            for (std::size_t k = 0; k < i; ++k) {
                item.dependencies.push_back(k);
            }
            record.items.push_back(std::move(item));
        }

        forward.push_back(std::move(record));
    }

    SparseForwardRecord terminal{};
    terminal.items.reserve(scalar_count);
    for (std::size_t i = 0; i < scalar_count; ++i) {
        SparseForwardItem item{};
        item.node = i;
        item.dependencies.reserve(i);
        for (std::size_t k = 0; k < i; ++k) {
            item.dependencies.push_back(k);
        }
        terminal.items.push_back(std::move(item));
    }
    forward.push_back(std::move(terminal));

    std::vector<SparseReverseRecord> reverse;
    reverse.reserve(scalar_count);
    for (std::size_t i = 0; i < scalar_count; ++i) {
        SparseReverseRecord record{};
        record.node = i;
        record.dependencies.reserve(
            scalar_count - i - 1u);
        for (std::size_t k = i + 1u;
             k < scalar_count;
             ++k) {
            record.dependencies.push_back(k);
        }
        reverse.push_back(std::move(record));
    }

    return {
        std::move(forward),
        std::move(reverse),
    };
}

}  // namespace shift::runtime::physics
