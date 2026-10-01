#include "shift_body_constraint_assembly.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::physics {
namespace {

struct ScalarRange {
    std::size_t base = 0;
    std::size_t width = 0;
    const char* kind = "";
    std::size_t index = 0;
};

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void validate_scalar_ranges(
    const BodyConstraintAssemblyInput& input) {

    if (input.scalar_count == 0) {
        throw std::invalid_argument(
            "BODY constraint scalar_count must be non-zero");
    }

    std::vector<ScalarRange> ranges;
    ranges.reserve(
        input.joints.size() +
        input.hinges.size() +
        input.bars.size());

    auto add = [&](std::size_t base,
                   std::size_t width,
                   const char* kind,
                   std::size_t index) {
        if (base > input.scalar_count ||
            width > input.scalar_count - base) {
            throw std::out_of_range(
                std::string(kind) +
                " scalar range is outside BODY solver domain");
        }
        ranges.push_back({base, width, kind, index});
    };

    for (std::size_t i = 0; i < input.joints.size(); ++i) {
        add(input.joints[i].scalar_base, 3u, "JOINT", i);
    }
    for (std::size_t i = 0; i < input.hinges.size(); ++i) {
        add(input.hinges[i].scalar_base, 2u, "HINGE", i);
    }
    for (std::size_t i = 0; i < input.bars.size(); ++i) {
        add(input.bars[i].scalar_base, 1u, "BAR", i);
    }

    std::sort(
        ranges.begin(),
        ranges.end(),
        [](const ScalarRange& left, const ScalarRange& right) {
            if (left.base != right.base) {
                return left.base < right.base;
            }
            return left.width < right.width;
        });
    for (std::size_t i = 1; i < ranges.size(); ++i) {
        const auto& previous = ranges[i - 1];
        const auto& current = ranges[i];
        if (current.base < previous.base + previous.width) {
            throw std::invalid_argument(
                "BODY constraint scalar ranges overlap");
        }
    }
}

std::array<double, 4> hinge_self_block(
    const HingeSelfBlockResult& self) {

    return {
        self.lower_triangle[0],
        0.0,
        self.lower_triangle[1],
        self.lower_triangle[2],
    };
}

std::vector<double> joint_self_block(
    const JointSelfBlockResult& self) {

    return {
        self.lower_triangle[0], 0.0, 0.0,
        self.lower_triangle[1], self.lower_triangle[2], 0.0,
        self.lower_triangle[3], self.lower_triangle[4],
        self.lower_triangle[5],
    };
}

}  // namespace

BodyConstraintAssemblyResult assemble_fun_007bc680_body_constraints(
    const BodyConstraintAssemblyInput& input) {

    require_finite(input.body_position, "BODY position");
    require_finite(input.body_tensor[0], "BODY tensor row 0");
    require_finite(input.body_tensor[1], "BODY tensor row 1");
    require_finite(input.body_tensor[2], "BODY tensor row 2");
    if (!std::isfinite(input.scales.linear_scale) ||
        !std::isfinite(input.scales.quadratic_scale)) {
        throw std::invalid_argument(
            "BODY constraint scales must be finite");
    }
    validate_scalar_ranges(input);

    BodyConstraintAssemblyResult result{};
    result.preprojection =
        evaluate_fun_007bc680_preprojection(
            input.preprojection);
    result.solver_vector.assign(
        input.scalar_count,
        0.0);
    result.lower_matrix.assign(
        input.scalar_count * input.scalar_count,
        0.0);

    // Retail FUN_007bc680 projection order:
    // JOINT -> HINGE -> BAR.
    for (const auto& sample : input.joints) {
        JointProjectionInput projection{};
        projection.body_position = input.body_position;
        projection.body_axis = input.preprojection.body_axis;
        projection.body_correction =
            input.preprojection.body_correction;
        projection.sample_position = sample.position;
        projection.residual_vector =
            result.preprojection.transformed_residual;
        projection.scaled_linear =
            result.preprojection.scaled_linear;
        projection.linear_scale = input.scales.linear_scale;
        projection.quadratic_scale =
            input.scales.quadratic_scale;
        projection.side_flag = sample.side_flag;
        const auto lanes =
            evaluate_fun_007bac60_joint(projection);
        result.solver_vector =
            apply_fun_007bac60_joint(
                result.solver_vector,
                sample.scalar_base,
                lanes.signed_lanes);
        ++result.joint_projection_count;
    }

    for (const auto& sample : input.hinges) {
        HingeProjectionInput projection{};
        projection.body_axis = input.preprojection.body_axis;
        projection.residual_vector =
            result.preprojection.transformed_residual;
        projection.sample_angular = sample.angular;
        projection.sample_linear = sample.linear;
        projection.sample_position = sample.position;
        projection.sample_frame_offset =
            sample.frame_offset;
        if (sample.side_flag != 0) {
            projection.body_frame =
                input.preprojection.body_frame;
        }
        projection.linear_scale = input.scales.linear_scale;
        projection.quadratic_scale =
            input.scales.quadratic_scale;
        projection.side_flag = sample.side_flag;
        const auto lanes =
            evaluate_fun_007bae40_hinge(projection);
        result.solver_vector =
            apply_fun_007bae40_hinge(
                result.solver_vector,
                sample.scalar_base,
                lanes.signed_lanes);
        ++result.hinge_projection_count;
    }

    for (const auto& sample : input.bars) {
        BarProjectionInput projection{};
        projection.body_position = input.body_position;
        projection.body_axis = input.preprojection.body_axis;
        projection.body_correction =
            input.preprojection.body_correction;
        projection.sample_position = sample.point;
        projection.sample_weight = sample.direction;
        projection.residual_vector =
            result.preprojection.transformed_residual;
        projection.scaled_linear =
            result.preprojection.scaled_linear;
        projection.linear_scale = input.scales.linear_scale;
        projection.quadratic_scale =
            input.scales.quadratic_scale;
        projection.side_bias = sample.side_bias;
        projection.side_flag = sample.side_flag;
        const auto lane =
            evaluate_fun_007bb090_bar(projection);
        result.solver_vector =
            apply_fun_007bb090_bar(
                result.solver_vector,
                sample.scalar_base,
                lane.signed_lane);
        ++result.bar_projection_count;
    }

    // Retail matrix ownership order:
    // JOINT self/mixed -> HINGE self/mixed -> BAR self/pairs.
    for (std::size_t i = 0; i < input.joints.size(); ++i) {
        const auto& outer = input.joints[i];
        const auto self =
            evaluate_fun_007bbb80_joint_self(
                input.body_tensor,
                outer.position,
                input.preprojection.inverse_scalar);
        result.lower_matrix =
            apply_fun_007bbb80_block(
                result.lower_matrix,
                input.scalar_count,
                outer.scalar_base,
                outer.scalar_base,
                joint_self_block(self),
                3u,
                3u);
        ++result.joint_matrix_self_count;

        for (std::size_t j = i + 1;
             j < input.joints.size();
             ++j) {
            const auto& inner = input.joints[j];
            const auto block =
                evaluate_fun_007bbb80_joint_joint(
                    input.body_tensor,
                    outer.position,
                    inner.position,
                    input.preprojection.inverse_scalar,
                    outer.scalar_base,
                    inner.scalar_base,
                    outer.side_flag == inner.side_flag);
            result.lower_matrix =
                apply_fun_007bbb80_block(
                    result.lower_matrix,
                    input.scalar_count,
                    block.row_base,
                    block.column_base,
                    block.block,
                    block.rows,
                    block.columns);
            ++result.joint_matrix_pair_count;
        }

        for (const auto& hinge : input.hinges) {
            const auto block =
                evaluate_fun_007bbb80_joint_hinge(
                    input.body_tensor,
                    outer.position,
                    hinge.angular,
                    hinge.linear,
                    outer.scalar_base,
                    hinge.scalar_base,
                    outer.side_flag == hinge.side_flag);
            result.lower_matrix =
                apply_fun_007bbb80_block(
                    result.lower_matrix,
                    input.scalar_count,
                    block.row_base,
                    block.column_base,
                    block.block,
                    block.rows,
                    block.columns);
            ++result.joint_matrix_pair_count;
        }

        for (const auto& bar : input.bars) {
            const auto block =
                evaluate_fun_007bbb80_joint_bar(
                    input.body_tensor,
                    outer.position,
                    bar.point,
                    bar.direction,
                    input.preprojection.inverse_scalar,
                    outer.scalar_base,
                    bar.scalar_base,
                    outer.side_flag == bar.side_flag);
            result.lower_matrix =
                apply_fun_007bbb80_block(
                    result.lower_matrix,
                    input.scalar_count,
                    block.row_base,
                    block.column_base,
                    block.block,
                    block.rows,
                    block.columns);
            ++result.joint_matrix_pair_count;
        }
    }

    for (std::size_t i = 0; i < input.hinges.size(); ++i) {
        const auto& outer = input.hinges[i];
        const auto self =
            evaluate_fun_007bb250_hinge_self(
                input.preprojection.body_frame,
                outer.angular,
                outer.linear);
        result.lower_matrix =
            apply_fun_007bb250_hinge_block(
                result.lower_matrix,
                input.scalar_count,
                outer.scalar_base,
                outer.scalar_base,
                hinge_self_block(self));
        ++result.hinge_matrix_self_count;

        for (std::size_t j = i + 1;
             j < input.hinges.size();
             ++j) {
            const auto& inner = input.hinges[j];
            const auto block =
                evaluate_fun_007bb250_hinge_pair(
                    input.preprojection.body_frame,
                    outer.angular,
                    outer.linear,
                    inner.angular,
                    inner.linear,
                    outer.scalar_base,
                    inner.scalar_base,
                    outer.side_flag == inner.side_flag);
            result.lower_matrix =
                apply_fun_007bb250_hinge_block(
                    result.lower_matrix,
                    input.scalar_count,
                    block.row_base,
                    block.column_base,
                    block.block);
            ++result.hinge_matrix_pair_count;
        }

        for (const auto& bar : input.bars) {
            const auto block =
                evaluate_fun_007bb250_hinge_bar(
                    input.preprojection.body_frame,
                    outer.angular,
                    outer.linear,
                    bar.point,
                    bar.direction,
                    outer.scalar_base,
                    bar.scalar_base,
                    outer.side_flag == bar.side_flag);
            result.lower_matrix =
                apply_fun_007bb250_hinge_bar_block(
                    result.lower_matrix,
                    input.scalar_count,
                    block.row_base,
                    block.column_base,
                    block.block,
                    block.rows,
                    block.columns);
            ++result.hinge_bar_pair_count;
        }
    }

    for (std::size_t i = 0; i < input.bars.size(); ++i) {
        const auto& outer = input.bars[i];
        const auto self =
            evaluate_fun_007bb6c0_bar_self(
                input.preprojection.body_frame,
                outer.point,
                outer.direction,
                input.preprojection.inverse_scalar);
        result.lower_matrix =
            apply_fun_007bb6c0_bar_scalar(
                result.lower_matrix,
                input.scalar_count,
                outer.scalar_base,
                outer.scalar_base,
                self.coefficient);
        ++result.bar_matrix_self_count;

        for (std::size_t j = i + 1;
             j < input.bars.size();
             ++j) {
            const auto& inner = input.bars[j];
            const auto pair =
                evaluate_fun_007bb6c0_bar_pair(
                    input.preprojection.body_frame,
                    outer.point,
                    outer.direction,
                    inner.point,
                    inner.direction,
                    input.preprojection.inverse_scalar,
                    outer.scalar_base,
                    inner.scalar_base,
                    outer.side_flag == inner.side_flag);
            result.lower_matrix =
                apply_fun_007bb6c0_bar_scalar(
                    result.lower_matrix,
                    input.scalar_count,
                    pair.row,
                    pair.column,
                    pair.coefficient);
            ++result.bar_matrix_pair_count;
        }
    }

    require_finite(
        result.solver_vector,
        "BODY assembled solver vector");
    require_finite(
        result.lower_matrix,
        "BODY assembled lower matrix");
    return result;
}

}  // namespace shift::runtime::physics
