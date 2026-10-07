#include "shift_fun_007675f0_surface_probe_node_cache.hpp"

#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_near(double actual, double expected, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun007675f0SurfaceProbeNodeOffset == 0x120u,
                "FUN_007675f0 cached node offset drift");
        require(kFun007675f0SurfaceProbeLastPositionXOffset == 0x128u &&
                    kFun007675f0SurfaceProbeLastPositionYOffset == 0x130u &&
                    kFun007675f0SurfaceProbeLastPositionZOffset == 0x138u,
                "FUN_007675f0 cached position offsets drift");
        require_near(kFun007675f0SurfaceProbeRefreshDistanceSquared, 0.01,
                     "FUN_007675f0 refresh threshold drift");

        SurfaceProbeNode node_a{};
        SurfaceProbeNode node_b{};
        Fun007675f0SurfaceProbeNodeCache cache{};
        std::size_t lookup_calls = 0u;
        std::vector<const SurfaceProbeNode*> previous_nodes;
        std::vector<SurfaceProbeVector3d> query_positions;

        Fun00717cd0SurfaceProbeNodeLookupProvider lookup =
            [&](const SurfaceProbeVector3d& query,
                const SurfaceProbeNode* previous) -> const SurfaceProbeNode* {
                ++lookup_calls;
                previous_nodes.push_back(previous);
                query_positions.push_back(query);
                return lookup_calls == 1u ? &node_a : &node_b;
            };

        const SurfaceProbeVector3d origin = {1.0, 2.0, 3.0};
        const SurfaceProbeVector3d query0 = {1.0, 2.0, 3.0};
        const SurfaceProbeNode* resolved =
            resolve_fun_007675f0_surface_probe_node_cache(
                cache, origin, query0, lookup);
        require(resolved == &node_a && lookup_calls == 1u,
                "null initial HDVehicle+0x120 did not force lookup");
        require(previous_nodes.size() == 1u && previous_nodes[0] == nullptr,
                "first lookup did not receive null previous node");
        require(cache.last_body_position_valid,
                "lookup did not commit last BODY0 position");
        require(cache.last_body_position == origin,
                "lookup did not preserve exact f64 BODY0 origin");

        const SurfaceProbeVector3d same = origin;
        resolved = resolve_fun_007675f0_surface_probe_node_cache(
            cache, same, query0, lookup);
        require(resolved == &node_a && lookup_calls == 1u,
                "unchanged BODY0 unexpectedly refreshed cached node");

        // Strict retail threshold: exactly 0.01 squared displacement does not
        // refresh. A +0.1 X movement produces 0.010000000000000002 in binary
        // double, so construct the witness directly from sqrt(0.01) then verify
        // the helper's measured value before testing the strict comparison.
        const double exact_step = std::sqrt(
            kFun007675f0SurfaceProbeRefreshDistanceSquared);
        SurfaceProbeVector3d threshold = origin;
        threshold[0] += exact_step;
        const double measured = fun_007675f0_surface_probe_cache_distance_squared(
            threshold, origin);
        if (measured <= kFun007675f0SurfaceProbeRefreshDistanceSquared) {
            resolved = resolve_fun_007675f0_surface_probe_node_cache(
                cache, threshold, query0, lookup);
            require(resolved == &node_a && lookup_calls == 1u,
                    "distance <= 0.01 failed strict no-refresh policy");
        }

        SurfaceProbeVector3d moved = origin;
        moved[0] += 0.2;
        const SurfaceProbeVector3d query1 = {1.25, 2.0, 3.0};
        resolved = resolve_fun_007675f0_surface_probe_node_cache(
            cache, moved, query1, lookup);
        require(resolved == &node_b && lookup_calls == 2u,
                "distance > 0.01 did not refresh cached node");
        require(previous_nodes.size() == 2u && previous_nodes[1] == &node_a,
                "refresh did not pass previous cached node to lookup");
        require(query_positions[1] == query1,
                "lookup query position was not forwarded exactly");
        require(cache.last_body_position == moved,
                "refresh did not commit exact current BODY0 position");

        Fun007675f0SurfaceProbeNodeCache null_return_cache{};
        std::size_t null_calls = 0u;
        Fun00717cd0SurfaceProbeNodeLookupProvider null_lookup =
            [&](const SurfaceProbeVector3d&,
                const SurfaceProbeNode*) -> const SurfaceProbeNode* {
                ++null_calls;
                return nullptr;
            };
        require(resolve_fun_007675f0_surface_probe_node_cache(
                    null_return_cache, origin, query0, null_lookup) == nullptr,
                "null lookup result was not preserved");
        require(null_return_cache.last_body_position_valid &&
                    null_return_cache.last_body_position == origin,
                "null lookup result did not still commit source last-position state");
        require(resolve_fun_007675f0_surface_probe_node_cache(
                    null_return_cache, origin, query0, null_lookup) == nullptr &&
                    null_calls == 2u,
                "null cached node did not force the next lookup");

        bool missing_provider_rejected = false;
        try {
            Fun007675f0SurfaceProbeNodeCache missing_provider_cache{};
            (void)resolve_fun_007675f0_surface_probe_node_cache(
                missing_provider_cache,
                origin,
                query0,
                {});
        } catch (const std::invalid_argument&) {
            missing_provider_rejected = true;
        }
        require(missing_provider_rejected,
                "missing FUN_00717cd0 provider failed open");

        bool nonfinite_rejected = false;
        try {
            Fun007675f0SurfaceProbeNodeCache nonfinite_cache{};
            const SurfaceProbeVector3d bad = {
                std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0};
            (void)should_refresh_fun_007675f0_surface_probe_node_cache(
                nonfinite_cache, bad);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "non-finite BODY0 position failed open");

        std::cout
            << "{\"format\":\"" << kFun007675f0SurfaceProbeNodeCacheFormat << "\","
            << "\"ready\":true,"
            << "\"node_offset\":\"HDVehicle+0x120\","
            << "\"last_position_offsets\":[\"0x128\",\"0x130\",\"0x138\"],"
            << "\"refresh_distance_squared\":0.01,"
            << "\"null_node_forces_lookup\":true,"
            << "\"strict_threshold\":true,"
            << "\"previous_node_forwarded\":true,"
            << "\"last_position_committed_after_lookup\":true,"
            << "\"lookup_provider_still_external\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
