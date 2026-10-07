#include "shift_fun_00766510_external_pass_input.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool near(double actual, double expected) {
    return std::abs(actual - expected) <= 1e-12;
}

Fun00765c40QueryInputBoundary selected_query_input() {
    Fun00765c40QueryInputBoundary input{};
    input.world_position = {10.0, 20.0, 30.0};
    input.cached_handle = std::nullopt;
    input.miss_fallback =
        selected_bmw_m3_e36_fun_00765c40_query_fallback();
    return input;
}

CollisionQueryOutput hit_output(
    const Fun00765c40QueryInputBoundary& input) {
    const auto query = build_fun_00765c40_query_record(input);
    CollisionSurfaceRecord surface{};
    surface.address_token = 0x1234u;
    surface.query_point = query.query_position;
    surface.normal = {0.0, 1.0, 0.0};
    surface.contact_height = 19.95;
    surface.triangle_a = {0.0, 0.0, 0.0};
    surface.triangle_b = {1.0, 0.0, 0.0};
    surface.triangle_c = {0.0, 0.0, 1.0};
    return apply_fun_007b0710_collision_query_result(query, surface);
}

}  // namespace

int main() {
    try {
        const auto query_input = selected_query_input();
        const auto hit = hit_output(query_input);
        const BodyAccumulatorVector3d application_point{4.0, 5.0, 6.0};

        const auto selected =
            build_fun_00766510_selected_bmw_external_pass_input(
                query_input,
                hit,
                application_point);
        validate_fun_00766510_external_pass_input(selected);
        require(selected.selected_bmw_domain,
                "Phase745 selected input lost BMW domain tag");
        require(selected.query_scalar_handoff.has_value(),
                "Phase745 selected input lost query-scalar handoff");
        require(selected.primary_application_point == application_point,
                "Phase745 selected input lost +0x38f0 application point");
        require(near(selected.query_scalar_handoff->query_scalar, 0.05),
                "Phase745 hit +0x38e0 projection mismatch");
        require(near(
                    selected.query_scalar_handoff->query_limit,
                    selected_bmw_m3_e36_fun_00765c40_query_fallback()),
                "Phase745 +0x38e8 query limit mismatch");
        require(near(selected.query_scalar_handoff->clamped_query_scalar, 0.05),
                "Phase745 hit clamp mismatch");

        const auto miss_record = build_fun_00765c40_query_record(query_input);
        const auto miss = apply_fun_007b0710_collision_query_result(
            miss_record,
            std::nullopt);
        const auto miss_input =
            build_fun_00766510_selected_bmw_external_pass_input(
                query_input,
                miss,
                application_point);
        const double fallback =
            selected_bmw_m3_e36_fun_00765c40_query_fallback();
        require(near(miss_input.query_scalar_handoff->query_scalar, fallback) &&
                    near(miss_input.query_scalar_handoff->query_limit, fallback) &&
                    near(miss_input.query_scalar_handoff->clamped_query_scalar, fallback),
                "Phase745 miss fallback/query-limit identity drift");

        Fun00766510ExternalPassInput generic{};
        validate_fun_00766510_external_pass_input(generic);

        bool incomplete_selected_rejected = false;
        try {
            Fun00766510ExternalPassInput incomplete{};
            incomplete.selected_bmw_domain = true;
            validate_fun_00766510_external_pass_input(incomplete);
        } catch (const std::invalid_argument&) {
            incomplete_selected_rejected = true;
        }
        require(incomplete_selected_rejected,
                "Phase745 incomplete selected input failed open");

        bool generic_claim_rejected = false;
        try {
            Fun00766510ExternalPassInput invalid{};
            invalid.primary_application_point = application_point;
            validate_fun_00766510_external_pass_input(invalid);
        } catch (const std::invalid_argument&) {
            generic_claim_rejected = true;
        }
        require(generic_claim_rejected,
                "Phase745 generic compatibility input claimed selected state");

        std::cout
            << "{\"format\":\"" << kFun00766510ExternalPassInputFormat << "\","
            << "\"ready\":true,"
            << "\"selected_query_handoff_owned\":true,"
            << "\"selected_application_point_owned\":true,"
            << "\"generic_compatibility_preserved\":true,"
            << "\"provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
