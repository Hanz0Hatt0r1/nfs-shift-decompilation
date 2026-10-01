#include "shift_constraint_relation_frame.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

ConstraintRefreshVector3d normalize_fun_00753690(
    ConstraintRefreshVector3d value) {

    require_finite(value, "FUN_00753690 vector");
    const long double length_sq =
        static_cast<long double>(value[0]) * value[0] +
        static_cast<long double>(value[1]) * value[1] +
        static_cast<long double>(value[2]) * value[2];
    if (!std::isfinite(length_sq)) {
        throw std::invalid_argument(
            "FUN_00753690 norm is non-finite");
    }
    if (length_sq == 0.0L) {
        return value;
    }

    const long double inverse_length =
        1.0L / std::sqrt(length_sq);
    for (double& component : value) {
        component = static_cast<double>(
            static_cast<long double>(component) *
            inverse_length);
    }
    require_finite(value, "FUN_00753690 result");
    return value;
}

void require_body_index(
    std::size_t index,
    std::size_t body_count,
    const char* label) {

    if (index >= body_count) {
        throw std::out_of_range(
            std::string(label) +
            " BODY index is outside relation frame");
    }
}

struct ScalarRange {
    std::size_t base = 0;
    std::size_t width = 0;
};

void validate_scalar_layout(
    const ConstraintRelationFrameInput& input) {

    if (input.scalar_count == 0) {
        throw std::invalid_argument(
            "constraint relation scalar_count must be non-zero");
    }

    std::vector<ScalarRange> ranges;
    ranges.reserve(
        input.joints.size() +
        input.hinges.size() +
        input.bars.size());

    auto add = [&](std::size_t base,
                   std::size_t width,
                   const char* label) {
        if (base > input.scalar_count ||
            width > input.scalar_count - base) {
            throw std::out_of_range(
                std::string(label) +
                " scalar range is outside relation domain");
        }
        ranges.push_back({base, width});
    };

    for (const auto& relation : input.joints) {
        add(relation.scalar_base, 3u, "JOINT");
    }
    for (const auto& relation : input.hinges) {
        add(relation.scalar_base, 2u, "HINGE");
    }
    for (const auto& relation : input.bars) {
        add(relation.scalar_base, 1u, "BAR");
    }

    std::sort(
        ranges.begin(),
        ranges.end(),
        [](const ScalarRange& left,
           const ScalarRange& right) {
            return std::tie(left.base, left.width) <
                std::tie(right.base, right.width);
        });

    std::size_t cursor = 0;
    for (const auto& range : ranges) {
        if (range.base != cursor) {
            throw std::invalid_argument(
                range.base < cursor
                    ? "constraint relation scalar ranges overlap"
                    : "constraint relation scalar layout has a gap");
        }
        cursor += range.width;
    }
    if (cursor != input.scalar_count) {
        throw std::invalid_argument(
            "constraint relation scalar layout does not cover scalar_count");
    }
}

ConstraintRelationSampleOwnership ownership(
    std::size_t relation_index,
    std::size_t body_index,
    std::size_t body_sample_ordinal,
    std::size_t scalar_base,
    std::uint8_t side_flag) {

    return {
        relation_index,
        body_index,
        body_sample_ordinal,
        scalar_base,
        side_flag,
    };
}

template <typename OwnershipRange>
const ConstraintRelationSampleOwnership& find_ownership(
    const OwnershipRange& rows,
    std::size_t relation_index,
    std::uint8_t side_flag) {

    const auto it = std::find_if(
        rows.begin(),
        rows.end(),
        [&](const auto& row) {
            return row.relation_index == relation_index &&
                row.side_flag == side_flag;
        });
    if (it == rows.end()) {
        throw std::runtime_error(
            "constraint relation ownership map is incomplete");
    }
    return *it;
}

}  // namespace

ConstraintRefreshVector3d inverse_transform_fun_007afcd0_relation(
    const ConstraintRefreshFrame3f& body_frame,
    const ConstraintRefreshVector3d& body_position,
    const ConstraintRefreshVector3d& world_value) {

    require_finite(
        body_position,
        "FUN_007afcd0 BODY position");
    require_finite(
        world_value,
        "FUN_007afcd0 world value");

    const ConstraintRefreshVector3d delta = {
        world_value[0] - body_position[0],
        world_value[1] - body_position[1],
        world_value[2] - body_position[2],
    };
    return transform_fun_007af0a0_refresh(
        body_frame,
        delta);
}

std::array<ConstraintRefreshVector3d, 3>
build_fun_007b1230_relation_basis(
    const ConstraintRefreshVector3d& local_primary) {

    auto primary =
        normalize_fun_00753690(local_primary);

    double seed_x = 0.0;
    double seed_y = 0.0;
    if (std::abs(primary[0]) >= 0.7) {
        seed_y = 1.0;
    } else {
        seed_x = 1.0;
    }

    ConstraintRefreshVector3d angular = {
        primary[1] * 0.0 - seed_y * primary[2],
        seed_x * primary[2] - primary[0] * 0.0,
        seed_y * primary[0] - primary[1] * seed_x,
    };
    ConstraintRefreshVector3d linear = {
        angular[2] * primary[1] -
            angular[1] * primary[2],
        angular[0] * primary[2] -
            primary[0] * angular[2],
        primary[0] * angular[1] -
            primary[1] * angular[0],
    };

    angular = normalize_fun_00753690(angular);
    linear = normalize_fun_00753690(linear);
    return {primary, angular, linear};
}

ConstraintRelationFrameResult
build_fun_007b3820_constraint_relation_frame(
    const ConstraintRelationFrameInput& input) {

    if (input.bodies.empty()) {
        throw std::invalid_argument(
            "constraint relation frame requires at least one BODY");
    }
    validate_scalar_layout(input);

    for (const auto& body : input.bodies) {
        require_finite(
            body.body_frame,
            "relation BODY frame");
        require_finite(
            body.body_position,
            "relation BODY position");
    }

    ConstraintRelationFrameResult result{};
    result.body_joints.resize(input.bodies.size());
    result.body_hinges.resize(input.bodies.size());
    result.body_bars.resize(input.bodies.size());
    result.joint_ownership.resize(input.bodies.size());
    result.hinge_ownership.resize(input.bodies.size());
    result.bar_ownership.resize(input.bodies.size());

    result.refresh_input.joints.reserve(
        input.joints.size());
    for (std::size_t index = 0;
         index < input.joints.size();
         ++index) {
        const auto& relation = input.joints[index];
        require_body_index(
            relation.positive_body_index,
            input.bodies.size(),
            "JOINT positive");
        require_body_index(
            relation.negative_body_index,
            input.bodies.size(),
            "JOINT negative");
        require_finite(
            relation.world_anchor,
            "JOINT world anchor");

        const auto& positive_body =
            input.bodies[relation.positive_body_index];
        const auto& negative_body =
            input.bodies[relation.negative_body_index];

        JointConstraintRefreshInput refresh{};
        refresh.positive_body_frame =
            positive_body.body_frame;
        refresh.negative_body_frame =
            negative_body.body_frame;
        refresh.positive_local_position =
            inverse_transform_fun_007afcd0_relation(
                positive_body.body_frame,
                positive_body.body_position,
                relation.world_anchor);
        refresh.negative_local_position =
            inverse_transform_fun_007afcd0_relation(
                negative_body.body_frame,
                negative_body.body_position,
                relation.world_anchor);
        result.refresh_input.joints.push_back(
            refresh);

        auto add = [&](std::size_t body_index,
                       std::uint8_t side_flag) {
            const std::size_t ordinal =
                result.body_joints[body_index].size();
            result.body_joints[body_index].push_back({
                {},
                relation.scalar_base,
                side_flag,
            });
            result.joint_ownership[body_index].push_back(
                ownership(
                    index,
                    body_index,
                    ordinal,
                    relation.scalar_base,
                    side_flag));
            ++result.body_sample_count;
        };

        // FUN_007b3820 allocates positive first, then negative.
        add(relation.positive_body_index, 1u);
        add(relation.negative_body_index, 0u);
    }

    result.refresh_input.hinges.reserve(
        input.hinges.size());
    for (std::size_t index = 0;
         index < input.hinges.size();
         ++index) {
        const auto& relation = input.hinges[index];
        require_body_index(
            relation.positive_body_index,
            input.bodies.size(),
            "HINGE positive");
        require_body_index(
            relation.negative_body_index,
            input.bodies.size(),
            "HINGE negative");
        require_finite(
            relation.world_axis,
            "HINGE world axis");

        const auto& positive_body =
            input.bodies[relation.positive_body_index];
        const auto& negative_body =
            input.bodies[relation.negative_body_index];

        const auto positive_local =
            transform_fun_007af0a0_refresh(
                positive_body.body_frame,
                relation.world_axis);
        const auto negative_local =
            transform_fun_007af0a0_refresh(
                negative_body.body_frame,
                relation.world_axis);
        const auto positive_basis =
            build_fun_007b1230_relation_basis(
                positive_local);
        const auto negative_basis =
            build_fun_007b1230_relation_basis(
                negative_local);

        HingeConstraintRefreshInput refresh{};
        refresh.positive_body_frame =
            positive_body.body_frame;
        refresh.negative_body_frame =
            negative_body.body_frame;
        refresh.positive_angular_local =
            positive_basis[1];
        refresh.positive_linear_local =
            positive_basis[2];
        refresh.negative_primary_local =
            negative_basis[0];
        result.refresh_input.hinges.push_back(
            refresh);

        const std::size_t positive_ordinal =
            result.body_hinges[
                relation.positive_body_index].size();
        result.body_hinges[
            relation.positive_body_index].push_back({
                {},
                {},
                positive_basis[0],
                {},
                relation.scalar_base,
                1u,
            });
        result.hinge_ownership[
            relation.positive_body_index].push_back(
                ownership(
                    index,
                    relation.positive_body_index,
                    positive_ordinal,
                    relation.scalar_base,
                    1u));
        ++result.body_sample_count;

        const std::size_t negative_ordinal =
            result.body_hinges[
                relation.negative_body_index].size();
        result.body_hinges[
            relation.negative_body_index].push_back({
                {},
                {},
                negative_basis[0],
                {},
                relation.scalar_base,
                0u,
            });
        result.hinge_ownership[
            relation.negative_body_index].push_back(
                ownership(
                    index,
                    relation.negative_body_index,
                    negative_ordinal,
                    relation.scalar_base,
                    0u));
        ++result.body_sample_count;
    }

    result.refresh_input.bars.reserve(
        input.bars.size());
    for (std::size_t index = 0;
         index < input.bars.size();
         ++index) {
        const auto& relation = input.bars[index];
        require_body_index(
            relation.positive_body_index,
            input.bodies.size(),
            "BAR positive");
        require_body_index(
            relation.negative_body_index,
            input.bodies.size(),
            "BAR negative");
        require_finite(
            relation.positive_world_anchor,
            "BAR positive world anchor");
        require_finite(
            relation.negative_world_anchor,
            "BAR negative world anchor");

        const auto& positive_body =
            input.bodies[relation.positive_body_index];
        const auto& negative_body =
            input.bodies[relation.negative_body_index];

        BarConstraintRefreshInput refresh{};
        refresh.positive_body_frame =
            positive_body.body_frame;
        refresh.negative_body_frame =
            negative_body.body_frame;
        refresh.positive_body_position =
            positive_body.body_position;
        refresh.negative_body_position =
            negative_body.body_position;
        refresh.positive_local_point =
            inverse_transform_fun_007afcd0_relation(
                positive_body.body_frame,
                positive_body.body_position,
                relation.positive_world_anchor);
        refresh.negative_local_point =
            inverse_transform_fun_007afcd0_relation(
                negative_body.body_frame,
                negative_body.body_position,
                relation.negative_world_anchor);
        result.refresh_input.bars.push_back(
            refresh);

        const long double dx =
            static_cast<long double>(
                relation.positive_world_anchor[0]) -
            relation.negative_world_anchor[0];
        const long double dy =
            static_cast<long double>(
                relation.positive_world_anchor[1]) -
            relation.negative_world_anchor[1];
        const long double dz =
            static_cast<long double>(
                relation.positive_world_anchor[2]) -
            relation.negative_world_anchor[2];
        const long double length_sq =
            dx * dx + dy * dy + dz * dz;
        if (!std::isfinite(length_sq)) {
            throw std::invalid_argument(
                "BAR relation length is non-finite");
        }
        const double side_bias =
            static_cast<double>(
                std::sqrt(length_sq));

        auto add = [&](std::size_t body_index,
                       std::uint8_t side_flag) {
            const std::size_t ordinal =
                result.body_bars[body_index].size();
            result.body_bars[body_index].push_back({
                {},
                {},
                side_bias,
                relation.scalar_base,
                side_flag,
            });
            result.bar_ownership[body_index].push_back(
                ownership(
                    index,
                    body_index,
                    ordinal,
                    relation.scalar_base,
                    side_flag));
            ++result.body_sample_count;
        };

        // FUN_007b3820 allocates positive first, then negative.
        add(relation.positive_body_index, 1u);
        add(relation.negative_body_index, 0u);
    }

    result.refreshed =
        refresh_fun_007b3ed0_constraints(
            result.refresh_input);

    for (std::size_t index = 0;
         index < input.joints.size();
         ++index) {
        const auto& relation = input.joints[index];
        const auto& refreshed =
            result.refreshed.joints[index];

        const auto& positive_ref =
            find_ownership(
                result.joint_ownership[
                    relation.positive_body_index],
                index,
                1u);
        const auto& negative_ref =
            find_ownership(
                result.joint_ownership[
                    relation.negative_body_index],
                index,
                0u);

        result.body_joints[
            relation.positive_body_index]
            [positive_ref.body_sample_ordinal]
            .position =
                refreshed.positive_position;
        result.body_joints[
            relation.negative_body_index]
            [negative_ref.body_sample_ordinal]
            .position =
                refreshed.negative_position;
    }

    for (std::size_t index = 0;
         index < input.hinges.size();
         ++index) {
        const auto& relation =
            input.hinges[index];
        const auto& refreshed =
            result.refreshed.hinges[index];

        const auto& positive_ref =
            find_ownership(
                result.hinge_ownership[
                    relation.positive_body_index],
                index,
                1u);
        const auto& negative_ref =
            find_ownership(
                result.hinge_ownership[
                    relation.negative_body_index],
                index,
                0u);

        auto& positive =
            result.body_hinges[
                relation.positive_body_index]
                [positive_ref.body_sample_ordinal];
        auto& negative =
            result.body_hinges[
                relation.negative_body_index]
                [negative_ref.body_sample_ordinal];

        positive.angular =
            refreshed.positive_angular;
        positive.linear =
            refreshed.positive_linear;
        negative.angular =
            refreshed.negative_angular;
        negative.linear =
            refreshed.negative_linear;

        // FUN_007bb8d0 fills only positive-side HINGE +0x78
        // from the negative sample's primary local row.
        positive.frame_offset =
            transform_fun_007aefb0_refresh(
                input.bodies[
                    relation.negative_body_index]
                    .body_frame,
                negative.position);
    }

    for (std::size_t index = 0;
         index < input.bars.size();
         ++index) {
        const auto& relation = input.bars[index];
        const auto& refreshed =
            result.refreshed.bars[index];

        const auto& positive_ref =
            find_ownership(
                result.bar_ownership[
                    relation.positive_body_index],
                index,
                1u);
        const auto& negative_ref =
            find_ownership(
                result.bar_ownership[
                    relation.negative_body_index],
                index,
                0u);

        auto& positive =
            result.body_bars[
                relation.positive_body_index]
                [positive_ref.body_sample_ordinal];
        auto& negative =
            result.body_bars[
                relation.negative_body_index]
                [negative_ref.body_sample_ordinal];

        positive.point =
            refreshed.positive_point;
        negative.point =
            refreshed.negative_point;
        positive.direction =
            refreshed.direction;
        negative.direction =
            refreshed.direction;
    }

    return result;
}

}  // namespace shift::runtime::physics
