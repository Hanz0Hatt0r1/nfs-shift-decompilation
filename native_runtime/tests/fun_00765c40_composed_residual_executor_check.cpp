#include "shift_fun_00765c40_composed_residual_executor.hpp"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using namespace shift::runtime::physics;
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
void put_f64(std::vector<std::uint8_t>& bytes, std::size_t body_index, std::size_t body_offset, double value) {
    const std::size_t offset = body_index * kBodyRecordSize + body_offset; std::uint64_t bits = 0u; std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) bytes[offset + byte] = static_cast<std::uint8_t>((bits >> (byte * 8u)) & 0xffu);
}
void put_f32(std::vector<std::uint8_t>& bytes, std::size_t body_index, std::size_t body_offset, float value) {
    const std::size_t offset = body_index * kBodyRecordSize + body_offset; std::uint32_t bits = 0u; std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) bytes[offset + byte] = static_cast<std::uint8_t>((bits >> (byte * 8u)) & 0xffu);
}
void put_origin(std::vector<std::uint8_t>& bytes, std::size_t body_index, double x, double y, double z) {
    put_f64(bytes, body_index, body_record_offset::kOrigin[0], x); put_f64(bytes, body_index, body_record_offset::kOrigin[1], y); put_f64(bytes, body_index, body_record_offset::kOrigin[2], z);
}
std::vector<std::uint8_t> make_selected_bmw_body_bytes() {
    std::vector<std::uint8_t> bytes(kBmwM3E36RetailBodyCount * kBodyRecordSize, 0u);
    put_origin(bytes, 0u, 100.0, 200.0, 300.0); put_origin(bytes, 3u, 10.0, 20.0, 30.0); put_origin(bytes, 4u, 14.0, 24.0, 34.0);
    put_f32(bytes, 0u, body_record_offset::kBasis[0], 1.0f); put_f32(bytes, 0u, body_record_offset::kBasis[4], 1.0f); put_f32(bytes, 0u, body_record_offset::kBasis[8], 1.0f); return bytes;
}
bool near(double actual, double expected) { return std::abs(actual - expected) <= 1e-12; }
}  // namespace

int main() {
    try {
        Fun00765c40ComposedResidualInputs inputs{};
        inputs.wheel_plane = {0x10u, 0x20u, 0x30u, 0x40u}; inputs.current_body_bytes = make_selected_bmw_body_bytes(); inputs.wheel_state_source_bits = 0x1122334455667788ull;
        bool queue_executed = false; std::size_t read_index = 0u; const Fun00765c40LoadTerms load_terms{1.0, -2.0, 3.5, 0.0};
        inputs.execute_wheel_job_queue = [&]() { queue_executed = true; };
        inputs.read_load_term = [&](std::size_t wheel) { require(queue_executed, "composed executor read load terms before queue execution"); require(wheel == read_index, "composed executor changed wheel load-term order"); ++read_index; return load_terms[wheel]; };
        inputs.persistent_write.positive_branch_values = {10.0, 20.0}; inputs.persistent_write.interpolation_result = 4.0f;
        for (std::size_t wheel = 0u; wheel < 4u; ++wheel) { inputs.wheel_pair.qword_bits[wheel][0] = 0x100u + wheel; inputs.wheel_pair.qword_bits[wheel][1] = 0x200u + wheel; }
        for (std::size_t slot = 0u; slot < kFun00765c40ContactArraySlotCount; ++slot) { inputs.contact_array.record_pointer_tokens[slot] = static_cast<std::uint32_t>(0x3000u + slot); inputs.contact_array.scalar_qword_bits[slot] = 0x4000u + slot; }
        inputs.contact_body_entries[0].apply = true; inputs.contact_body_entries[0].point_or_lever_arm = {1.0, 0.0, 0.0}; inputs.contact_body_entries[0].contribution = {0.0, 2.0, 0.0};
        inputs.bounded_state_tail.write_block_executed = true; inputs.bounded_state_tail.state_3668_bits = 0xaaaau; inputs.bounded_state_tail.state_3670_bits = 0xbbbbu; inputs.bounded_state_tail.state_3678_bits = 0xccccu;
        inputs.optional_body_sweep.enabled = true; inputs.optional_body_sweep.entries[0].point_or_lever_arm = {0.0, 1.0, 0.0}; inputs.optional_body_sweep.entries[0].contribution = {0.0, 0.0, 3.0};
        std::size_t scene_query_calls = 0u;
        const auto result = execute_fun_00765c40_composed_residual_pass(inputs, [&](const Fun00765c40SceneQueryBoundary& boundary) { ++scene_query_calls; CollisionQueryOutput output{}; output.query_record = build_fun_00765c40_query_record(boundary.query_input); return output; });
        require(result.executed_stage_order == kFun00765c40ResidualStageOrder, "composed executor residual stage trace drift");
        require(result.wheel_plane.qword_bits == inputs.wheel_plane, "composed executor wheel-plane payload drift");
        require(scene_query_calls == 1u && near(result.query_commit.projected_scalar, selected_bmw_m3_e36_fun_00765c40_query_fallback()), "composed executor native scene-query miss fallback drift");
        require(read_index == 4u && result.wheel_job.load_terms == load_terms, "composed executor wheel-job seam drift");
        for (std::size_t wheel = 0u; wheel < kFun00765c40WheelCount; ++wheel) { require(result.wheel_state_assignments[wheel].index == wheel, "composed executor wheel-state index drift"); require(result.wheel_state_assignments[wheel].source_bits == inputs.wheel_state_source_bits, "composed executor wheel-state source drift"); }
        require(near(result.persistent_write.wheel_values[0], 10.0) && near(result.persistent_write.wheel_values[1], 0.0) && result.persistent_write.filtered_value == 4.0f, "composed executor FUN_007584f0 materialization drift");
        require(result.positive_load_count == 2u, "composed executor positive load count drift");
        require(result.wheel_pair.qword_bits == inputs.wheel_pair.qword_bits, "composed executor wheel-pair payload drift");
        require(result.contact_array.record_pointer_tokens == inputs.contact_array.record_pointer_tokens && result.contact_array.scalar_qword_bits == inputs.contact_array.scalar_qword_bits, "composed executor contact-array payload drift");
        require(result.contact_body.applied_entry_count == 1u, "composed executor contact BODY count drift");
        require(result.bounded_state_tail.has_value() && result.bounded_state_tail->flag_3660 == 1u && result.bounded_state_tail->state_3668_bits == 0xaaaau && result.bounded_state_tail->state_3670_bits == 0xbbbbu && result.bounded_state_tail->state_3678_bits == 0xccccu, "composed executor bounded state-tail drift");
        require(result.optional_body_sweep.executed && result.optional_body_sweep.applied_entry_count == 4u, "composed executor optional BODY sweep drift");
        require(near(result.optional_body_sweep.body.linear[1], 2.0) && near(result.optional_body_sweep.body.linear[2], 3.0) && near(result.optional_body_sweep.body.angular[2], 2.0) && near(result.optional_body_sweep.body.angular[0], 3.0), "composed executor BODY accumulation order drift");
        bool rejected_missing_scene_query = false; try { (void)execute_fun_00765c40_composed_residual_pass(inputs, {}); } catch (const std::invalid_argument&) { rejected_missing_scene_query = true; }
        require(rejected_missing_scene_query, "composed executor accepted missing scene-query boundary");
        std::cout << "{\"format\":\"" << kFun00765c40ComposedResidualExecutorFormat << "\",\"ready\":true,\"stage_count\":11,\"scene_query_external\":true,\"query_fallback_native\":true,\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) { std::cerr << exc.what() << '\n'; return 1; }
}
