#include "shift_fun_0076d100_anchor_sequence.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

Fun0076d100AnchorSequenceResult execute_fun_0076d100_required_anchor_sequence(
    const Fun0076d100AnchorCallback& contact_factor,
    const Fun0076d100AnchorCallback& wheel_update,
    const Fun0076d100AnchorCallback& contact_response,
    const Fun0076d100AnchorCallback& contact_outer,
    const Fun0076d100AnchorCallback& motion_read_gate) {
    if (!contact_factor || !wheel_update || !contact_response ||
        !contact_outer || !motion_read_gate) {
        throw std::invalid_argument(
            "FUN_0076d100 required-anchor sequence needs all callback boundaries");
    }

    Fun0076d100AnchorSequenceResult result{};

    contact_factor();
    ++result.contact_factor_count;

    wheel_update();
    ++result.wheel_update_count;

    contact_response();
    ++result.contact_response_count;

    // The Ghidra frontier uniquely recovers FUN_00769ef0 as the direct
    // FUN_0076d100 tail callee that contains these two anchors in order.
    ++result.tail_invocation_count;
    contact_outer();
    ++result.contact_outer_count;
    motion_read_gate();
    ++result.motion_read_gate_count;

    return result;
}

}  // namespace shift::runtime::physics
