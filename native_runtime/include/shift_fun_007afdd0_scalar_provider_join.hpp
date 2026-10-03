#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_fun_007afdd0_source_core.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007afdd0ScalarProviderJoinFormat =
    "SHIFT.NativeFun007afdd0ScalarProviderJoin/1";

using Fun007afdd0ScalarProvider = std::function<Fun007afdd0ScalarBoundary(
    std::size_t body_index,
    const ConstraintRefreshFrame3f& basis,
    const BodyFrameIntegrationVector3d& rotation_increment)>;

struct Fun007afdd0ScalarProviderJoinResult {
    std::vector<std::uint8_t> body_bytes{};
    std::size_t provider_call_count = 0u;
    std::size_t applied_rotation_count = 0u;
    std::size_t zero_noop_count = 0u;
};

Fun007afdd0ScalarProviderJoinResult
execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count,
    double timestep,
    const Fun007afdd0ScalarProvider& scalar_provider);

}  // namespace shift::runtime::physics
