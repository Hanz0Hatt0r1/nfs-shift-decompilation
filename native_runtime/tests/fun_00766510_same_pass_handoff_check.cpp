#include "shift_fun_00766510_external_pass_input.hpp"
#include "shift_fun_00766510_selected_bmw_application_point.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <iostream>
#include <stdexcept>

namespace {
using namespace shift::runtime;
using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
}

int main() {
    try {
        Fun00765c40QueryInputBoundary query_input{};
        query_input.world_position = {1.0, 2.0, 3.0};
        query_input.cached_handle = std::nullopt;
        query_input.miss_fallback = 0.10000000149011612;
        const auto record = build_fun_00765c40_query_record(query_input);
        const auto output = apply_fun_007b0710_collision_query_result(record, std::nullopt);
        const auto handoff = execute_fun_00765c40_to_00766510_query_scalar_handoff(
            query_input, output);

        Fun00766510ExternalPassInput selected{};
        selected.selected_bmw_domain = true;
        selected.query_scalar_handoff = handoff;
        selected.primary_application_point = BodyAccumulatorVector3d{4.0, 5.0, 6.0};
        validate_fun_00766510_external_pass_input(selected);
        require(selected.query_scalar_handoff->query_scalar == query_input.miss_fallback,
                "Phase745 miss handoff did not preserve +0x38e8 scalar");
        require(selected.query_scalar_handoff->clamped_query_scalar == query_input.miss_fallback,
                "Phase745 miss handoff did not preserve clamp result");

        Fun00766510ExternalPassInput generic{};
        validate_fun_00766510_external_pass_input(generic);

        bool incomplete_rejected = false;
        try {
            Fun00766510ExternalPassInput incomplete{};
            incomplete.selected_bmw_domain = true;
            incomplete.query_scalar_handoff = handoff;
            validate_fun_00766510_external_pass_input(incomplete);
        } catch (const std::invalid_argument&) {
            incomplete_rejected = true;
        }
        require(incomplete_rejected,
                "Phase745 selected input accepted missing +0x38f0 application point");

        std::size_t legacy_calls = 0u;
        NativeVehicleContactResponseProvider legacy =
            [&legacy_calls](std::size_t) { ++legacy_calls; };
        legacy(0u, generic);
        require(legacy_calls == 1u,
                "Phase745 legacy fixture adapter did not preserve pass-only callback");

        bool typed_saw_selected = false;
        NativeVehicleContactResponseProvider typed =
            [&typed_saw_selected](std::size_t,
                                  const Fun00766510ExternalPassInput& input) {
                typed_saw_selected = input.selected_bmw_domain &&
                    input.query_scalar_handoff.has_value() &&
                    input.primary_application_point.has_value();
            };
        typed(1u, selected);
        require(typed_saw_selected,
                "Phase745 typed provider did not receive selected same-pass input");

        std::cout << "{\"format\":\"" << kFun00766510ExternalPassInputFormat
                  << "\",\"ready\":true,\"selected_requires_query_handoff\":true,"
                  << "\"selected_requires_application_point\":true,"
                  << "\"legacy_fixture_adapter\":true,\"provider_count\":7}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
