#include "fun_00770e80_outer_update_fixture.hpp"
#include "shift_fun_00769ef0_param3.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

void configure_runtime(
    NativeRuntimeState& runtime,
    const std::vector<std::uint8_t>& initial_body_bytes) {
    runtime.physics.workspace.configure(2u, 1u, 1u);
    runtime.physics.participant_contract_ready = true;
    runtime.physics.participant_registry_ready = true;
    runtime.physics.selector_context_separate = true;
    runtime.physics.participant_ready = true;
    runtime.physics.participant_identity_join_proven = true;
    runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);
}

}  // namespace

int main() {
    try {
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto machine_input = make_machine_input();
        auto initial_body_bytes = make_raw_bodies(projection.bodies);
        put_f64(initial_body_bytes, kFun00769ef0Body0Field120Offset, 1.0);

        NativeRuntimeState runtime{};
        configure_runtime(runtime, initial_body_bytes);

        NativeVehicleExternalProviderBundle bundle{};
        bundle.fun_00765c40 = [](
            std::size_t pass,
            const Fun00765c40ExternalPassInput& input) {
            Fun00765c40QueryInputBoundary query_input{};
            query_input.world_position = {
                static_cast<double>(pass),
                1.0 + static_cast<double>(pass),
                2.0 + static_cast<double>(pass)};
            query_input.cached_handle = input.cached_handle;
            query_input.miss_fallback = 5.0;
            return Fun00765c40ExternalPassResult{
                Fun00765c40LoadTerms{3000.0, 3000.0, 3000.0, 3000.0},
                query_input,
                2000u + static_cast<std::uint64_t>(pass)};
        };
        bundle.wheel_update = [](std::size_t) {};
        bundle.contact_response = [](std::size_t) {};
        bundle.contact_outer_input = [](std::size_t) {
            return make_contact_outer_input();
        };
        bundle.motion_read_setup.caller_gate_open = false;
        bundle.scalar_provider_factory = [](std::size_t) {
            return [](std::size_t,
                      const ConstraintRefreshFrame3f&,
                      const BodyFrameIntegrationVector3d&) {
                Fun007afdd0ScalarBoundary scalars{};
                scalars.squared_magnitude_test = 0.0f;
                scalars.sqrt_magnitude = 0.0f;
                scalars.sine = 0.0f;
                scalars.cosine = 1.0f;
                return scalars;
            };
        };
        bundle.half_step_refresh =
            [&source,
             &relations,
             &reset_state,
             &solver_topology,
             &projection,
             &machine_input](
                std::size_t,
                double,
                const std::vector<std::uint8_t>&) {
                NativeVehicleHalfStepRefreshInput input{};
                input.machine = machine_input;
                input.source = source;
                input.relations = relations;
                input.reset_state = reset_state;
                input.solver_topology = solver_topology;
                input.projection = projection;
                return input;
            };
        bundle.post_half_step = [](std::size_t) {};

        NativeVehicleProviderSession session(std::move(bundle));
        const auto result = session.execute_explicit_step(runtime, 0.5);

        constexpr std::uint32_t kExpectedSteeringBits = 0xc0236e05u;
        require(result.joined.motion_read_input_present[0] &&
                    result.joined.motion_read_input_present[1],
                "FUN_007594e0 session inputs were not captured for both passes");
        require(result.fun_00765c40_query_input_present[0] &&
                    result.fun_00765c40_query_input_present[1],
                "FUN_00765c40 query inputs were not captured for both passes");
        require(!result.fun_00765c40_query_inputs[0].cached_handle.has_value() &&
                    result.fun_00765c40_query_inputs[1].cached_handle == 2000u,
                "FUN_00765c40 persistent query cache input did not advance between passes");
        require(result.fun_00765c40_returned_cache_handles[0] == 2000u &&
                    result.fun_00765c40_returned_cache_handles[1] == 2001u &&
                    session.fun_00765c40_query_cache_handle() == 2001u,
                "FUN_00765c40 returned query cache state did not commit");
        require(
            f32_bits(result.joined.motion_read_inputs[0].steering) ==
                kExpectedSteeringBits,
            "FUN_007594e0 pass-0 session steering mismatch");
        require(
            f32_bits(result.joined.motion_read_inputs[1].steering) ==
                kExpectedSteeringBits,
            "FUN_007594e0 pass-1 session steering mismatch");
        require(
            result.joined.motion_read_inputs[0].steering ==
                result.joined.motion_read_inputs[1].steering,
            "FUN_007594e0 steering refreshed between the two retail passes");
        require(
            result.joined.motion_read_inputs[0].load_terms ==
                Fun00765c40LoadTerms{3000.0, 3000.0, 3000.0, 3000.0} &&
            result.joined.motion_read_inputs[1].load_terms ==
                Fun00765c40LoadTerms{3000.0, 3000.0, 3000.0, 3000.0},
            "FUN_00765c40 typed load terms were not consumed by both passes");
        require(!result.joined.motion_read_inputs[0].caller_gate_open &&
                    !result.joined.motion_read_inputs[1].caller_gate_open,
                "FUN_007560c0 setup gate changed between passes");
        require(
            result.joined.motion_read_inputs[0].angle_mode ==
                kBmwNativeSilverstonePlayerDifficulty &&
            result.joined.motion_read_inputs[1].angle_mode ==
                kBmwNativeSilverstonePlayerDifficulty,
            "selected native Player Difficulty changed between passes");

        std::cout
            << "{\"format\":\"SHIFT.NativeFun007594e0SessionAngle/1\","
            << "\"ready\":true,"
            << "\"external_gate_field_present\":false,"
            << "\"external_steering_field_present\":false,"
            << "\"external_load_term_fields_present\":false,"
            << "\"external_angle_mode_field_present\":false,"
            << "\"selected_player_difficulty\":"
            << kBmwNativeSilverstonePlayerDifficulty << ","
            << "\"fun_00765c40_result_typed\":true,"
            << "\"fun_00765c40_cache_owned\":true,"
            << "\"derived_before_pass0\":true,"
            << "\"same_value_used_by_both_passes\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
