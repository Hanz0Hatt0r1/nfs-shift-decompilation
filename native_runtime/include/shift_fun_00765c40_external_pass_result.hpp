#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"

#include <cmath>
#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/4";
inline constexpr const char* kFun00765c40ExternalPassInputFormat =
    "SHIFT.Fun00765c40ExternalPassInput/2";

struct Fun00765c40ExternalPassInput {
    std::optional<CollisionQueryVector3d> world_position{};
    std::optional<std::uint64_t> cached_handle{};

    std::optional<double> selected_bmw_miss_fallback() const {
        if (!world_position.has_value()) {
            return std::nullopt;
        }
        return selected_bmw_m3_e36_fun_00765c40_query_fallback();
    }

    std::optional<Fun00765c40QueryInputBoundary> selected_bmw_query_input() const {
        if (!world_position.has_value()) {
            return std::nullopt;
        }
        Fun00765c40QueryInputBoundary query{};
        query.world_position = *world_position;
        query.cached_handle = cached_handle;
        query.miss_fallback = selected_bmw_m3_e36_fun_00765c40_query_fallback();
        validate_fun_00765c40_query_input_boundary(query);
        return query;
    }
};

struct Fun00765c40ExternalPassResult {
    Fun00765c40LoadTerms load_terms{};
    Fun00765c40QueryInputBoundary query_input{};
    std::optional<std::uint64_t> returned_cache_handle{};
    std::optional<CollisionQueryOutput> query_output{};
};

inline void validate_fun_00765c40_collision_output_handoff(
    const Fun00765c40QueryInputBoundary& query_input,
    const CollisionQueryOutput& output) {
    const auto expected = build_fun_00765c40_query_record(query_input);

    if (output.query_record.query_position != expected.query_position ||
        output.query_record.y_tolerance != expected.y_tolerance ||
        output.query_record.max_aux != expected.max_aux ||
        output.query_record.cache_enabled != expected.cache_enabled) {
        throw std::invalid_argument(
            "FUN_00765c40 collision output does not belong to the typed query input");
    }
    for (double value : output.normal) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00765c40 collision output normal must be finite");
        }
    }

    if (output.hit) {
        if (!output.contact_height.has_value() ||
            !output.returned_handle.has_value() ||
            !output.query_record.output_height.has_value() ||
            !output.query_record.cache_handle.has_value()) {
            throw std::invalid_argument(
                "FUN_00765c40 hit output is incomplete");
        }
        if (!std::isfinite(*output.contact_height) ||
            *output.query_record.output_height != *output.contact_height ||
            *output.query_record.cache_handle != *output.returned_handle) {
            throw std::invalid_argument(
                "FUN_00765c40 hit output fields disagree");
        }
    } else {
        if (output.contact_height.has_value() ||
            output.returned_handle.has_value() ||
            output.query_record.output_height.has_value() ||
            output.query_record.cache_handle != expected.cache_handle) {
            throw std::invalid_argument(
                "FUN_00765c40 miss output fields disagree");
        }
    }

    const bool expected_reuse =
        output.hit && query_input.cached_handle.has_value() &&
        output.returned_handle.has_value() &&
        *query_input.cached_handle == *output.returned_handle;
    if (output.reused_cache != expected_reuse) {
        throw std::invalid_argument(
            "FUN_00765c40 collision output cache-reuse flag disagrees with query state");
    }
}

inline void validate_fun_00765c40_external_pass_result(
    const Fun00765c40ExternalPassInput& input,
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_load_terms(result.load_terms);
    validate_fun_00765c40_query_input_boundary(result.query_input);

    const auto native_selected_query = input.selected_bmw_query_input();
    if (native_selected_query.has_value()) {
        if (result.query_input.world_position != native_selected_query->world_position ||
            result.query_input.cached_handle != native_selected_query->cached_handle ||
            result.query_input.miss_fallback != native_selected_query->miss_fallback) {
            throw std::invalid_argument(
                "FUN_00765c40 residual provider changed native-owned selected query input");
        }
    } else if (result.query_input.cached_handle != input.cached_handle) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned cached handle");
    }

    if (input.world_position.has_value() && !result.query_output.has_value()) {
        throw std::invalid_argument(
            "FUN_00765c40 selected BMW provider hid FUN_007b0710 collision output");
    }
    if (result.query_output.has_value()) {
        validate_fun_00765c40_collision_output_handoff(
            result.query_input,
            *result.query_output);
        if (result.returned_cache_handle != result.query_output->returned_handle) {
            throw std::invalid_argument(
                "FUN_00765c40 returned cache handle disagrees with FUN_007b0710 output");
        }
    }
}

}  // namespace shift::runtime::physics
