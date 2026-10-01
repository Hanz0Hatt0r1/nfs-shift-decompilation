#pragma once

#include "shift_hinge_matrix_coupling.hpp"

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

struct HingeBarPairResult {
    HingeMatrixRows transformed_hinge{};
    std::array<double, 2> raw_coefficients{};
    std::vector<double> block;
    std::size_t rows = 0;
    std::size_t columns = 0;
    std::size_t row_base = 0;
    std::size_t column_base = 0;
    double sign = 1.0;
    std::string orientation;
};

HingeBarPairResult evaluate_fun_007bb250_hinge_bar(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& hinge_angular,
    const std::array<double, 3>& hinge_linear,
    const std::array<double, 3>& bar_point,
    const std::array<double, 3>& bar_direction,
    std::size_t hinge_base,
    std::size_t bar_base,
    bool same_side);

std::vector<double> apply_fun_007bb250_hinge_bar_block(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row_base,
    std::size_t column_base,
    const std::vector<double>& block,
    std::size_t rows,
    std::size_t columns);

}  // namespace shift::runtime::physics
