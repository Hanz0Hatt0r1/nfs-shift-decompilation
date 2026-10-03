#include "shift_fun_007afdd0_scalar_provider_join.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

Fun007afdd0ScalarProviderJoinResult
execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count,
    double timestep,
    const Fun007afdd0ScalarProvider& scalar_provider) {
    if (!scalar_provider) {
        throw std::invalid_argument(
            "FUN_007afdd0 source-core integration requires a scalar provider");
    }

    Fun007afdd0ScalarProviderJoinResult result{};
    std::size_t next_body_index = 0u;

    const BodyBasisRotationCallback basis_rotation =
        [&](const ConstraintRefreshFrame3f& basis,
            const BodyFrameIntegrationVector3d& rotation_increment) {
            if (next_body_index >= body_count) {
                throw std::logic_error(
                    "FUN_007afdd0 scalar provider invoked outside BODY domain");
            }

            const std::size_t body_index = next_body_index;
            const auto scalars = scalar_provider(
                body_index,
                basis,
                rotation_increment);
            const auto core = execute_fun_007afdd0_source_core(
                basis,
                rotation_increment,
                scalars);

            ++next_body_index;
            ++result.provider_call_count;
            if (core.applied) {
                ++result.applied_rotation_count;
            } else {
                ++result.zero_noop_count;
            }
            return core.basis;
        };

    result.body_bytes = execute_fun_007b2270_body_buffer_with_basis_callback(
        body_bytes,
        body_count,
        timestep,
        basis_rotation);

    if (next_body_index != body_count ||
        result.provider_call_count != body_count) {
        throw std::logic_error(
            "FUN_007afdd0 scalar-provider BODY iteration count mismatch");
    }
    return result;
}

}  // namespace shift::runtime::physics
