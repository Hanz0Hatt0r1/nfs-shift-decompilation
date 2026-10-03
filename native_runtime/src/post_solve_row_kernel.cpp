#include "shift_post_solve_projection.hpp"
#include "shift_body_accumulator_primitives.hpp"

#include <array>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::physics {
namespace {

void require_finite_body(const BodyAccumulatorState& body) {
    for (double value : body.angular) {
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "post-solve row kernel has non-finite angular BODY state");
        }
    }
    for (double value : body.linear) {
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "post-solve row kernel has non-finite linear BODY state");
        }
    }
}

void require_row_range(
    std::size_t base,
    std::size_t width,
    std::size_t scalar_count,
    const char* label) {

    if (base >= scalar_count || width > scalar_count - base) {
        throw std::runtime_error(
            std::string("post-solve row kernel ") + label +
            " scalar range out of range");
    }
}

}  // namespace

std::vector<BodyAccumulatorState> apply_post_solve_body_projection_rows(
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<double>& solver_vector,
    const std::vector<BodyAccumulatorState>& initial_bodies) {

    if (initial_bodies.size() != projection.bodies.size()) {
        throw std::runtime_error(
            "post-solve row kernel BODY cardinality mismatch");
    }
    if (solver_vector.size() != projection.solver_vector.size()) {
        throw std::runtime_error(
            "post-solve row kernel scalar cardinality mismatch");
    }
    for (double value : solver_vector) {
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "post-solve row kernel solved vector contains non-finite value");
        }
    }
    for (const auto& body : initial_bodies) {
        require_finite_body(body);
    }

    std::vector<BodyAccumulatorState> bodies = initial_bodies;
    const std::size_t scalar_count = solver_vector.size();

    for (const auto& row : projection.joints) {
        if (row.positive_body >= bodies.size() ||
            row.negative_body >= bodies.size()) {
            throw std::runtime_error(
                "post-solve row kernel JOINT BODY index out of range");
        }
        require_row_range(row.scalar_base, 3u, scalar_count, "JOINT");
        const std::array<double, 3> contribution = {
            solver_vector[row.scalar_base + 0u],
            solver_vector[row.scalar_base + 1u],
            solver_vector[row.scalar_base + 2u],
        };
        apply_fun_007baa70_body_accumulator(
            bodies[row.positive_body],
            row.positive_lever_arm,
            contribution);
        apply_fun_007baaf0_body_accumulator(
            bodies[row.negative_body],
            row.negative_lever_arm,
            contribution);
    }

    for (const auto& row : projection.hinges) {
        if (row.positive_body >= bodies.size() ||
            row.negative_body >= bodies.size()) {
            throw std::runtime_error(
                "post-solve row kernel HINGE BODY index out of range");
        }
        require_row_range(row.scalar_base, 2u, scalar_count, "HINGE");
        const double s0 = solver_vector[row.scalar_base + 0u];
        const double s1 = solver_vector[row.scalar_base + 1u];
        for (std::size_t component = 0; component < 3; ++component) {
            bodies[row.positive_body].angular[component] +=
                row.positive_angular_row[component] * s0 +
                row.positive_linear_row[component] * s1;
            bodies[row.negative_body].angular[component] -=
                row.negative_angular_row[component] * s0 +
                row.negative_linear_row[component] * s1;
        }
    }

    for (const auto& row : projection.bars) {
        if (row.positive_body >= bodies.size() ||
            row.negative_body >= bodies.size()) {
            throw std::runtime_error(
                "post-solve row kernel BAR BODY index out of range");
        }
        require_row_range(row.scalar_base, 1u, scalar_count, "BAR");
        const double scalar = solver_vector[row.scalar_base];
        const std::array<double, 3> contribution = {
            row.direction[0] * scalar,
            row.direction[1] * scalar,
            row.direction[2] * scalar,
        };
        apply_fun_007baa70_body_accumulator(
            bodies[row.positive_body],
            row.positive_lever_arm,
            contribution);
        apply_fun_007baaf0_body_accumulator(
            bodies[row.negative_body],
            row.negative_lever_arm,
            contribution);
    }

    for (const auto& body : bodies) {
        require_finite_body(body);
    }
    return bodies;
}

}  // namespace shift::runtime::physics
