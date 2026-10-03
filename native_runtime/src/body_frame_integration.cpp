#include "shift_body_frame_integration.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

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

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

void require_state(
    const BodyFrameIntegrationState& state,
    const char* label) {

    require_finite(state.origin, label);
    require_finite(state.cross_vector, label);
    require_finite(state.prepared_vector, label);
    require_finite(state.accumulators.angular, label);
    require_finite(state.accumulators.linear, label);
    require_finite(state.motion_triplet, label);
    require_finite_value(state.scalar_0x90, label);
    require_finite(state.reciprocal_coefficients, label);
    require_finite(state.basis, label);
}

ConstraintRefreshFrame3f flatten_tensor(const BodyTensor3f& tensor) {
    ConstraintRefreshFrame3f result{};
    for (std::size_t row = 0; row < 3u; ++row) {
        for (std::size_t column = 0; column < 3u; ++column) {
            result[row * 3u + column] = tensor[row][column];
        }
    }
    return result;
}

}  // namespace

BodyFramePreBasisResult advance_fun_007bab70_pre_basis(
    const BodyFrameIntegrationState& state,
    double timestep) {

    require_state(state, "FUN_007bab70 input BODY state");
    require_finite_value(timestep, "FUN_007bab70 timestep");

    BodyFramePreBasisResult result{};
    result.state = state;

    // Retail source order: origin consumes the incoming motion triplet before
    // accumulator_b changes that motion triplet for subsequent integration.
    for (std::size_t component = 0; component < 3u; ++component) {
        result.state.origin[component] +=
            state.motion_triplet[component] * timestep;
    }
    require_finite(result.state.origin, "FUN_007bab70 updated origin");

    const double motion_scale = state.scalar_0x90 * timestep;
    require_finite_value(motion_scale, "FUN_007bab70 motion scale");
    for (std::size_t component = 0; component < 3u; ++component) {
        result.state.motion_triplet[component] +=
            state.accumulators.linear[component] * motion_scale;
        result.rotation_increment[component] =
            state.cross_vector[component] * timestep;
    }
    require_finite(
        result.state.motion_triplet,
        "FUN_007bab70 updated motion triplet");
    require_finite(
        result.rotation_increment,
        "FUN_007bab70 rotation increment");

    return result;
}

BodyFrameIntegrationResult complete_fun_007bab70_post_basis(
    const BodyFramePreBasisResult& pre_basis,
    const ConstraintRefreshFrame3f& basis_after_fun_007afdd0,
    double timestep) {

    require_state(pre_basis.state, "FUN_007bab70 pre-basis BODY state");
    require_finite(
        pre_basis.rotation_increment,
        "FUN_007bab70 rotation increment");
    require_finite(
        basis_after_fun_007afdd0,
        "FUN_007bab70 basis after FUN_007afdd0");
    require_finite_value(timestep, "FUN_007bab70 timestep");

    BodyFrameIntegrationResult result{};
    result.state = pre_basis.state;
    result.rotation_increment = pre_basis.rotation_increment;
    result.state.basis = basis_after_fun_007afdd0;

    // The retail basis writer runs before these lanes.  Requiring the caller to
    // provide its output prevents the tensor from being rebuilt against a stale
    // basis while FUN_007afdd0 remains an independently gated helper.
    for (std::size_t component = 0; component < 3u; ++component) {
        result.state.prepared_vector[component] +=
            result.state.accumulators.angular[component] * timestep;
    }
    require_finite(
        result.state.prepared_vector,
        "FUN_007bab70 updated prepared vector");

    result.symmetric_tensor =
        build_fun_007ba630_body_tensor(
            result.state.reciprocal_coefficients,
            result.state.basis);
    const auto tensor_matrix = flatten_tensor(result.symmetric_tensor);
    result.state.cross_vector =
        transform_fun_007aefb0_refresh(
            tensor_matrix,
            result.state.prepared_vector);
    require_state(result.state, "FUN_007bab70 output BODY state");
    return result;
}

BodyFrameIntegrationResult execute_fun_007bab70_with_external_basis(
    const BodyFrameIntegrationState& state,
    const ConstraintRefreshFrame3f& basis_after_fun_007afdd0,
    double timestep) {

    const auto pre_basis =
        advance_fun_007bab70_pre_basis(state, timestep);
    return complete_fun_007bab70_post_basis(
        pre_basis,
        basis_after_fun_007afdd0,
        timestep);
}

std::vector<BodyFrameIntegrationResult>
execute_fun_007b2270_body_array_with_external_bases(
    const std::vector<BodyFrameIntegrationState>& bodies,
    const std::vector<ConstraintRefreshFrame3f>& bases_after_fun_007afdd0,
    double timestep) {

    require_finite_value(timestep, "FUN_007b2270 timestep");
    if (bodies.size() != bases_after_fun_007afdd0.size()) {
        throw std::invalid_argument(
            "FUN_007b2270 BODY/basis array sizes must match");
    }

    std::vector<BodyFrameIntegrationResult> result;
    result.reserve(bodies.size());
    for (std::size_t index = 0; index < bodies.size(); ++index) {
        result.push_back(
            execute_fun_007bab70_with_external_basis(
                bodies[index],
                bases_after_fun_007afdd0[index],
                timestep));
    }
    return result;
}

}  // namespace shift::runtime::physics
