#pragma once

#include "shift_fun_00765c40_query_input_boundary.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

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

}  // namespace shift::runtime::physics
