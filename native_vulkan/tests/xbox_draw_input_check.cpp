#include "shift_xbox_draw_input.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

const uint8_t kCapturedPacket[] = {
    0xC0, 0x03, 0x22, 0x01,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x00, 0x04,
    0x09, 0x75, 0xD7, 0xB0,
    0x40, 0x00, 0x00, 0x06,
};

uint32_t read_be32(const uint8_t* bytes) {
    return (static_cast<uint32_t>(bytes[0]) << 24) |
           (static_cast<uint32_t>(bytes[1]) << 16) |
           (static_cast<uint32_t>(bytes[2]) << 8) | bytes[3];
}

void write_be32(uint8_t* bytes, uint32_t value) {
    bytes[0] = static_cast<uint8_t>(value >> 24);
    bytes[1] = static_cast<uint8_t>(value >> 16);
    bytes[2] = static_cast<uint8_t>(value >> 8);
    bytes[3] = static_cast<uint8_t>(value);
}

}  // namespace

int main() {
    const uint8_t shader_control_flow[] = {
        0x00, 0x01, 0x10, 0x02, 0x00, 0x02, 0x10, 0x00, 0xC4, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x10, 0x02, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    std::vector<shift::xbox::CapturedShaderControlFlow> control_flow;
    std::string error;
    require(shift::xbox::decode_captured_shader_control_flow(
                shader_control_flow, sizeof(shader_control_flow), &control_flow, &error),
            "bounded shader control-flow prefix was rejected");
    require(control_flow.size() == 4, "shader control-flow slot count changed");
    require(control_flow[0].instruction_index == 0 &&
                control_flow[0].opcode == shift::xbox::ShaderControlFlowOpcode::Exec &&
                control_flow[0].address == 2 && control_flow[0].instruction_count == 1 &&
                control_flow[0].sequence == 1,
            "shader exec scheduling fields changed");
    require(control_flow[1].instruction_index == 1 &&
                control_flow[1].opcode == shift::xbox::ShaderControlFlowOpcode::Allocate &&
                control_flow[1].allocation_size == 2 &&
                control_flow[1].allocation_type == 2,
            "shader export allocation fields changed");
    require(control_flow[2].opcode == shift::xbox::ShaderControlFlowOpcode::ExecEnd &&
                control_flow[2].address == 2 && control_flow[2].instruction_count == 1,
            "shader exec-end fields changed");
    require(control_flow[3].opcode == shift::xbox::ShaderControlFlowOpcode::Nop,
            "shader control-flow NOP changed");

    const uint8_t shader_branch_control_flow[] = {
        0x00, 0x00, 0x10, 0x04, 0x00, 0x02, 0x10, 0x00, 0xB6, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x20, 0x03, 0x10, 0x04, 0xB0, 0x00, 0x20, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    std::vector<shift::xbox::CapturedShaderControlFlow> branch_control_flow;
    require(shift::xbox::decode_captured_shader_control_flow(
                shader_branch_control_flow, sizeof(shader_branch_control_flow),
                &branch_control_flow, &error),
            "shader control-flow branches were rejected");
    require(branch_control_flow.size() == 8 &&
                branch_control_flow[1].opcode ==
                    shift::xbox::ShaderControlFlowOpcode::ConditionalJump &&
                branch_control_flow[1].address == 2 &&
                branch_control_flow[1].bool_constant == 128 &&
                branch_control_flow[1].condition &&
                !branch_control_flow[1].unconditional &&
                branch_control_flow[2].opcode ==
                    shift::xbox::ShaderControlFlowOpcode::ConditionalJump &&
                branch_control_flow[2].address == 3 &&
                branch_control_flow[2].unconditional,
            "shader conditional and unconditional jump fields changed");

    shift::xbox::CapturedShaderControlFlow fetch_clause{};
    fetch_clause.instruction_index = 4;
    fetch_clause.opcode = shift::xbox::ShaderControlFlowOpcode::Exec;
    fetch_clause.address = 2;
    fetch_clause.instruction_count = 2;
    fetch_clause.sequence = 9;
    shift::xbox::CapturedShaderControlFlow branch_clause{};
    branch_clause.instruction_index = 5;
    branch_clause.opcode = shift::xbox::ShaderControlFlowOpcode::ConditionalJump;
    shift::xbox::CapturedShaderControlFlow end_clause{};
    end_clause.instruction_index = 6;
    end_clause.opcode = shift::xbox::ShaderControlFlowOpcode::ExecEnd;
    end_clause.address = 4;
    end_clause.instruction_count = 1;
    end_clause.sequence = 2;
    const std::vector<shift::xbox::CapturedShaderControlFlow> scheduled_control_flow = {
        fetch_clause, branch_clause, end_clause,
    };
    std::vector<shift::xbox::CapturedShaderInstructionSchedule> instruction_schedule;
    require(shift::xbox::schedule_captured_shader_instructions(
                scheduled_control_flow, 6 * 12, &instruction_schedule, &error),
            "shader exec clauses did not produce an instruction schedule");
    require(instruction_schedule.size() == 3 && instruction_schedule[0].address == 2 &&
                instruction_schedule[0].kind ==
                    shift::xbox::ShaderScheduledInstructionKind::Fetch &&
                instruction_schedule[0].control_flow_index == 4 &&
                instruction_schedule[1].address == 3 &&
                instruction_schedule[1].kind ==
                    shift::xbox::ShaderScheduledInstructionKind::Alu &&
                instruction_schedule[1].serialized && instruction_schedule[2].address == 4 &&
                instruction_schedule[2].serialized,
            "shader sequence kind/serialization fields changed");
    const auto unchanged_schedule = instruction_schedule;
    require(!shift::xbox::schedule_captured_shader_instructions(
                scheduled_control_flow, 4 * 12, &instruction_schedule, &error) &&
                instruction_schedule.size() == unchanged_schedule.size() &&
                instruction_schedule[0].address == unchanged_schedule[0].address,
            "out-of-range shader schedule was accepted or changed its output");

    uint8_t vertex_shader_fetch_bytes[12];
    write_be32(vertex_shader_fetch_bytes, 0x82343840u);
    write_be32(vertex_shader_fetch_bytes + 4, 0x00070123u);
    write_be32(vertex_shader_fetch_bytes + 8, 0x7FFFFE05u);
    uint8_t texture_shader_fetch_bytes[12];
    write_be32(texture_shader_fetch_bytes, 0x0C702081u);
    write_be32(texture_shader_fetch_bytes + 4, 0x00000555u);
    write_be32(texture_shader_fetch_bytes + 8, 0x80004000u);
    shift::xbox::CapturedShaderFetchInstruction fetch{};
    require(shift::xbox::decode_captured_shader_fetch_instruction(
                vertex_shader_fetch_bytes, sizeof(vertex_shader_fetch_bytes), &fetch, &error),
            "captured vfetch_full instruction was rejected");
    require(fetch.kind == shift::xbox::CapturedShaderFetchKind::VertexFull &&
                fetch.fetch_constant_index == 10 && fetch.source_register == 2 &&
                fetch.destination_register == 3 && fetch.source_swizzle == 2 &&
                fetch.destination_swizzle == 0x123 && fetch.vertex_format == 7 &&
                fetch.vertex_stride == 5 && fetch.vertex_offset == -2 &&
                fetch.source_relative && fetch.destination_relative,
            "vfetch_full fields changed");
    const shift::xbox::CapturedShaderFetchInstruction full_fetch = fetch;
    uint8_t vertex_shader_mini_fetch_bytes[12];
    write_be32(vertex_shader_mini_fetch_bytes, 0x42604060u);
    write_be32(vertex_shader_mini_fetch_bytes + 4, 0x40070123u);
    write_be32(vertex_shader_mini_fetch_bytes + 8, 0x7FFFFF00u);
    require(shift::xbox::decode_captured_shader_fetch_instruction(
                vertex_shader_mini_fetch_bytes,
                sizeof(vertex_shader_mini_fetch_bytes), &fetch, &error),
            "captured vfetch_mini instruction was rejected");
    require(fetch.kind == shift::xbox::CapturedShaderFetchKind::VertexMini &&
                fetch.fetch_constant_index == 19 && fetch.source_register == 3 &&
                fetch.destination_register == 4 && fetch.source_swizzle == 1 &&
                fetch.destination_swizzle == 0x123 && fetch.vertex_format == 7 &&
                fetch.vertex_stride == 0 && fetch.vertex_offset == -1 &&
                !fetch.source_relative && !fetch.destination_relative,
            "vfetch_mini fields changed");
    shift::xbox::CapturedShaderFetchInstruction effective_mini_fetch{};
    require(shift::xbox::inherit_captured_vertex_fetch_fields(
                fetch, &full_fetch, &effective_mini_fetch, &error) &&
                effective_mini_fetch.kind ==
                    shift::xbox::CapturedShaderFetchKind::VertexMini &&
                effective_mini_fetch.fetch_constant_index == 10 &&
                effective_mini_fetch.source_register == 2 &&
                effective_mini_fetch.source_swizzle == 2 &&
                effective_mini_fetch.vertex_stride == 5 &&
                effective_mini_fetch.vertex_format == 7 &&
                effective_mini_fetch.vertex_offset == -1 &&
                effective_mini_fetch.destination_register == 4 &&
                effective_mini_fetch.source_relative &&
                !effective_mini_fetch.destination_relative,
            "vfetch_mini did not inherit the full-fetch addressing fields");
    require(!shift::xbox::inherit_captured_vertex_fetch_fields(
                fetch, nullptr, &effective_mini_fetch, &error) &&
                error == "captured mini vertex fetch has no preceding full fetch",
            "mini vertex fetch without a full fetch was accepted");
    require(shift::xbox::decode_captured_shader_fetch_instruction(
                texture_shader_fetch_bytes, sizeof(texture_shader_fetch_bytes), &fetch, &error),
            "captured tfetch2D instruction was rejected");
    require(fetch.kind == shift::xbox::CapturedShaderFetchKind::Texture2D &&
                fetch.fetch_constant_index == 7 && fetch.texture_dimension == 1 &&
                fetch.source_register == 4 && fetch.destination_register == 2 &&
                fetch.source_swizzle == 3 && fetch.destination_swizzle == 0x555 &&
                fetch.predicate_condition,
            "tfetch2D fields changed");
    require(!shift::xbox::decode_captured_shader_fetch_instruction(
                vertex_shader_fetch_bytes, sizeof(vertex_shader_fetch_bytes) - 1,
                &fetch, &error),
            "truncated shader fetch instruction was accepted");
    uint8_t unsupported_shader_fetch[sizeof(vertex_shader_fetch_bytes)];
    std::copy(vertex_shader_fetch_bytes,
              vertex_shader_fetch_bytes + sizeof(vertex_shader_fetch_bytes),
              unsupported_shader_fetch);
    unsupported_shader_fetch[3] = 0x42;
    require(!shift::xbox::decode_captured_shader_fetch_instruction(
                unsupported_shader_fetch, sizeof(unsupported_shader_fetch), &fetch, &error),
            "unsupported shader fetch opcode was accepted");

    uint8_t alu_instruction_bytes[12];
    const uint32_t alu_word0 =
        1u | (1u << 6) | (1u << 7) | (2u << 8) | (1u << 14) | (1u << 15) |
        (0xAu << 16) | (5u << 20) | (1u << 24) | (37u << 26);
    const uint32_t alu_word1 = 0xFF563412u;
    const uint32_t alu_word2 = 0xBCC18243u;
    write_be32(alu_instruction_bytes, alu_word0);
    write_be32(alu_instruction_bytes + 4, alu_word1);
    write_be32(alu_instruction_bytes + 8, alu_word2);
    shift::xbox::CapturedShaderAluInstruction alu{};
    require(shift::xbox::decode_captured_shader_alu_instruction(
                alu_instruction_bytes, sizeof(alu_instruction_bytes), &alu, &error),
            "96-bit shader ALU instruction was rejected");
    require(alu.vector_opcode == 28 && alu.scalar_opcode == 37 &&
                alu.vector_destination == 1 && alu.scalar_destination == 2 &&
                alu.vector_write_mask == 0xA && alu.scalar_write_mask == 5 &&
                alu.export_data && alu.vector_destination_relative &&
                alu.scalar_destination_relative && alu.absolute_constants &&
                alu.vector_clamp && !alu.scalar_clamp && alu.predicated &&
                alu.predicate_condition && alu.const0_relative && alu.const1_relative &&
                alu.const_address_register_relative &&
                alu.source_registers[0] == 0xC1 && alu.source_registers[1] == 0x82 &&
                alu.source_registers[2] == 0x43 && alu.source_temporary_registers[0] == 1 &&
                alu.source_temporary_registers[1] == 2 && alu.source_temporary_registers[2] == 3 &&
                alu.source_temporary_relative[0] && !alu.source_temporary_relative[1] &&
                alu.source_temporary_relative[2] && alu.source_temporary_absolute[0] &&
                !alu.source_temporary_absolute[1] && !alu.source_temporary_absolute[2] &&
                alu.scalar_temporary_register == 19 &&
                alu.scalar_temporary_component == 2 &&
                alu.scalar_constant_component == 3 && alu.source_swizzles[0] == 0x56 &&
                alu.source_swizzles[1] == 0x34 && alu.source_swizzles[2] == 0x12 &&
                alu.source_is_temporary[0] && !alu.source_is_temporary[1] &&
                alu.source_is_temporary[2] && alu.source_negate[0] &&
                alu.source_negate[1] && alu.source_negate[2],
            "shader ALU bit fields changed");
    require(shift::xbox::captured_alu_source_component(0x1Bu, 0) == 3 &&
                shift::xbox::captured_alu_source_component(0x1Bu, 1) == 3 &&
                shift::xbox::captured_alu_source_component(0x1Bu, 2) == 3 &&
                shift::xbox::captured_alu_source_component(0x1Bu, 3) == 3 &&
                shift::xbox::captured_alu_source_component(0xAAu, 0) == 2 &&
                shift::xbox::captured_alu_source_component(0xAAu, 1) == 3 &&
                shift::xbox::captured_alu_source_component(0xAAu, 2) == 0 &&
                shift::xbox::captured_alu_source_component(0xAAu, 3) == 1,
            "component-relative ALU swizzles changed");
    require(!shift::xbox::decode_captured_shader_alu_instruction(
                alu_instruction_bytes, sizeof(alu_instruction_bytes) - 1, &alu, &error),
            "truncated shader ALU instruction was accepted");

    std::vector<shift::xbox::CapturedShaderControlFlow> unchanged_control_flow = control_flow;
    require(!shift::xbox::decode_captured_shader_control_flow(
                shader_control_flow, sizeof(shader_control_flow) - 4,
                &control_flow, &error),
            "truncated shader control-flow input was accepted");
    require(control_flow.size() == unchanged_control_flow.size(),
            "failed shader decode partially replaced its output");
    uint8_t unsupported_shader_control_flow[sizeof(shader_control_flow)];
    std::copy(shader_control_flow, shader_control_flow + sizeof(shader_control_flow),
              unsupported_shader_control_flow);
    unsupported_shader_control_flow[6] = 0xF0;
    require(!shift::xbox::decode_captured_shader_control_flow(
                unsupported_shader_control_flow, sizeof(unsupported_shader_control_flow),
                &control_flow, &error),
            "unsupported shader control-flow opcode was accepted");
    require(control_flow.size() == unchanged_control_flow.size(),
            "unsupported shader decode partially replaced its output");

    const uint8_t framed_stream[] = {
        0x00, 0x01, 0x12, 0x34, 0xAA, 0xBB, 0xCC, 0xDD, // type 0, base 0x1234
        0x01, 0x02, 0x03, 0x04,
        0x40, 0x1A, 0xA8, 0x21, 0x11, 0x22, 0x33, 0x44, // type 1, regs 0x21/0x355
        0x55, 0x66, 0x77, 0x88,
        0x80, 0x00, 0x00, 0x00,                         // type 2
        0x00, 0x00, 0x00, 0x00,                         // single-dword zero NOP
        0xC0, 0x03, 0x22, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x06, 0x00, 0x04, 0x09, 0x75, 0xD7, 0xB0,
        0x40, 0x00, 0x00, 0x06,                         // type 3 DRAW_INDX
    };
    std::vector<shift::xbox::PacketSpan> packet_spans;
    require(shift::xbox::scan_captured_packet_stream(
                framed_stream, sizeof(framed_stream), &packet_spans, &error),
            "well-formed PM4 packet stream was rejected");
    require(packet_spans.size() == 5, "PM4 packet scanner returned the wrong packet count");
    require(packet_spans[0].type == shift::xbox::PacketType::Type0 &&
                packet_spans[0].byte_offset == 0 && packet_spans[0].byte_length == 12,
            "type-0 framing changed");
    require(packet_spans[1].type == shift::xbox::PacketType::Type1 &&
                packet_spans[1].byte_offset == 12 && packet_spans[1].byte_length == 12,
            "type-1 framing changed");
    require(packet_spans[2].type == shift::xbox::PacketType::Type2 &&
                packet_spans[2].byte_offset == 24 && packet_spans[2].byte_length == 4,
            "type-2 framing changed");
    require(packet_spans[3].type == shift::xbox::PacketType::ZeroNop &&
                packet_spans[3].byte_offset == 28 && packet_spans[3].byte_length == 4,
            "zero-dword NOP framing changed");
    require(packet_spans[4].type == shift::xbox::PacketType::Type3 &&
                packet_spans[4].byte_offset == 32 && packet_spans[4].byte_length == 20 &&
                packet_spans[4].opcode == 0x22,
            "type-3 DRAW_INDX framing changed");
    const uint8_t captured_indirect_buffer[] = {
        0xC0, 0x01, 0x3F, 0x00, 0x09, 0x75, 0xB6, 0x60,
        0x00, 0x00, 0x00, 0x4A,
    };
    shift::xbox::CapturedIndirectBuffer indirect_buffer{};
    require(shift::xbox::decode_captured_indirect_buffer(
                captured_indirect_buffer, sizeof(captured_indirect_buffer),
                &indirect_buffer, &error) &&
                indirect_buffer.guest_address == 0x0975B660u &&
                indirect_buffer.dword_count == 74u,
            "captured PM4_INDIRECT_BUFFER span decoded incorrectly");
    auto invalid_indirect_buffer = std::vector<uint8_t>(
        captured_indirect_buffer,
        captured_indirect_buffer + sizeof(captured_indirect_buffer));
    invalid_indirect_buffer[11] = 0x00;
    const auto unchanged_indirect_buffer = indirect_buffer;
    require(!shift::xbox::decode_captured_indirect_buffer(
                invalid_indirect_buffer.data(), invalid_indirect_buffer.size(),
                &indirect_buffer, &error) &&
                indirect_buffer.guest_address == unchanged_indirect_buffer.guest_address &&
                indirect_buffer.dword_count == unchanged_indirect_buffer.dword_count,
            "invalid PM4_INDIRECT_BUFFER changed decoded output");
    std::vector<shift::xbox::GuestRegisterWrite> register_writes;
    require(shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[0].byte_offset,
                packet_spans[0].byte_length, &register_writes, &error) &&
                register_writes.size() == 2 &&
                register_writes[0].register_index == 0x1234u &&
                register_writes[0].value == 0xAABBCCDDu &&
                register_writes[1].register_index == 0x1235u &&
                register_writes[1].value == 0x01020304u,
            "type-0 PM4 register writes decoded incorrectly");
    require(shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[1].byte_offset,
                packet_spans[1].byte_length, &register_writes, &error) &&
                register_writes.size() == 2 &&
                register_writes[0].register_index == 0x21u &&
                register_writes[0].value == 0x11223344u &&
                register_writes[1].register_index == 0x355u &&
                register_writes[1].value == 0x55667788u,
            "type-1 PM4 register writes decoded incorrectly");
    const uint8_t repeated_register_packet[] = {
        0x00, 0x01, 0x80, 0x12, 0x11, 0x11, 0x11, 0x11,
        0x22, 0x22, 0x22, 0x22,
    };
    require(shift::xbox::decode_guest_register_writes(
                repeated_register_packet, sizeof(repeated_register_packet),
                &register_writes, &error) && register_writes.size() == 2 &&
                register_writes[0].register_index == 0x12u &&
                register_writes[1].register_index == 0x12u,
            "type-0 write-one-register mode decoded incorrectly");
    const auto unchanged_writes = register_writes;
    require(!shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[2].byte_offset,
                packet_spans[2].byte_length, &register_writes, &error) &&
                register_writes.size() == unchanged_writes.size() &&
                register_writes[0].register_index == unchanged_writes[0].register_index &&
                register_writes[0].value == unchanged_writes[0].value &&
                register_writes[1].register_index == unchanged_writes[1].register_index &&
                register_writes[1].value == unchanged_writes[1].value,
            "unsupported PM4 packet changed register-write output");
    require(!shift::xbox::decode_guest_register_writes(
                framed_stream + packet_spans[0].byte_offset, 8u,
                &register_writes, &error) &&
                register_writes.size() == unchanged_writes.size(),
            "truncated type-0 PM4 packet changed register-write output");
    const uint8_t captured_vertex_im_load[] = {
        0xC0, 0x01, 0x27, 0x00, 0x09, 0xD5, 0x68, 0xE0, 0x00, 0x00, 0x00, 0x69,
    };
    const uint8_t captured_pixel_im_load[] = {
        0xC0, 0x01, 0x27, 0x00, 0x09, 0xD5, 0x04, 0x61, 0x00, 0x00, 0x00, 0x1E,
    };
    shift::xbox::CapturedShaderProgramLoad shader_load{};
    require(shift::xbox::decode_captured_shader_program_load(
                captured_vertex_im_load, sizeof(captured_vertex_im_load),
                &shader_load, &error) &&
                shader_load.stage == shift::xbox::GuestShaderStage::Vertex &&
                shader_load.guest_address == 0x09D568E0u &&
                shader_load.dword_count == 105u && shader_load.byte_length == 420u,
            "captured vertex PM4_IM_LOAD span decoded incorrectly");
    require(shift::xbox::decode_captured_shader_program_load(
                captured_pixel_im_load, sizeof(captured_pixel_im_load),
                &shader_load, &error) &&
                shader_load.stage == shift::xbox::GuestShaderStage::Pixel &&
                shader_load.guest_address == 0x09D50460u &&
                shader_load.dword_count == 30u && shader_load.byte_length == 120u,
            "captured pixel PM4_IM_LOAD span decoded incorrectly");
    const auto unchanged_shader_load = shader_load;
    uint8_t invalid_shader_load[sizeof(captured_pixel_im_load)];
    std::copy_n(captured_pixel_im_load, sizeof(captured_pixel_im_load),
                invalid_shader_load);
    invalid_shader_load[7] = 0x62;
    require(!shift::xbox::decode_captured_shader_program_load(
                invalid_shader_load, sizeof(invalid_shader_load), &shader_load, &error) &&
                shader_load.stage == unchanged_shader_load.stage &&
                shader_load.guest_address == unchanged_shader_load.guest_address &&
                shader_load.byte_length == unchanged_shader_load.byte_length,
            "unsupported shader stage changed decoded output");
    const uint8_t captured_inline_shader_load[] = {
        0xC0, 0x05, 0x2B, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x03,
        0x11, 0x22, 0x33, 0x44,
        0x55, 0x66, 0x77, 0x88,
        0x99, 0xAA, 0xBB, 0xCC,
        0xDE, 0xAD, 0xBE, 0xEF,
    };
    shift::xbox::CapturedImmediateShaderProgramLoad immediate_shader_load{};
    require(shift::xbox::decode_captured_immediate_shader_program_load(
                captured_inline_shader_load, sizeof(captured_inline_shader_load),
                &immediate_shader_load, &error) &&
                immediate_shader_load.stage == shift::xbox::GuestShaderStage::Vertex &&
                immediate_shader_load.dword_count == 3u &&
                immediate_shader_load.byte_length == 12u &&
                immediate_shader_load.code_offset == 12u &&
                read_be32(captured_inline_shader_load + immediate_shader_load.code_offset) ==
                    0x11223344u,
            "captured inline vertex shader payload decoded incorrectly");
    auto captured_pixel_inline_shader_load = std::vector<uint8_t>(
        captured_inline_shader_load,
        captured_inline_shader_load + sizeof(captured_inline_shader_load));
    captured_pixel_inline_shader_load[7] = 0x01;
    require(shift::xbox::decode_captured_immediate_shader_program_load(
                captured_pixel_inline_shader_load.data(),
                captured_pixel_inline_shader_load.size(), &immediate_shader_load, &error) &&
                immediate_shader_load.stage == shift::xbox::GuestShaderStage::Pixel &&
                immediate_shader_load.dword_count == 3u &&
                immediate_shader_load.code_offset == 12u,
            "captured inline pixel shader payload decoded incorrectly");
    const auto unchanged_immediate_shader_load = immediate_shader_load;
    auto invalid_immediate_shader_load = captured_pixel_inline_shader_load;
    invalid_immediate_shader_load[7] = 0x02;
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                invalid_immediate_shader_load.data(),
                invalid_immediate_shader_load.size(), &immediate_shader_load, &error) &&
                immediate_shader_load.stage == unchanged_immediate_shader_load.stage &&
                immediate_shader_load.dword_count == unchanged_immediate_shader_load.dword_count &&
                immediate_shader_load.code_offset == unchanged_immediate_shader_load.code_offset,
            "unsupported inline shader stage changed decoded output");
    invalid_immediate_shader_load = captured_pixel_inline_shader_load;
    invalid_immediate_shader_load[9] = 0x01;
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                invalid_immediate_shader_load.data(),
                invalid_immediate_shader_load.size(), &immediate_shader_load, &error),
            "nonzero inline shader start address was accepted");
    invalid_immediate_shader_load = captured_pixel_inline_shader_load;
    invalid_immediate_shader_load[11] = 0x05;
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                invalid_immediate_shader_load.data(),
                invalid_immediate_shader_load.size(), &immediate_shader_load, &error),
            "inline shader code span larger than its PM4 payload was accepted");
    require(!shift::xbox::decode_captured_immediate_shader_program_load(
                captured_inline_shader_load, sizeof(captured_inline_shader_load) - 4u,
                &immediate_shader_load, &error),
            "truncated inline shader PM4 packet was accepted");
    const uint8_t captured_constant_load_packet[] = {
        0xC0, 0x02, 0x2F, 0x00, 0x09, 0xD5, 0x68, 0xA0,
        0x00, 0x00, 0x03, 0xF0, 0x00, 0x00, 0x00, 0x10,
    };
    shift::xbox::CapturedConstantLoad constant_load{};
    require(shift::xbox::decode_captured_constant_load(
                captured_constant_load_packet, sizeof(captured_constant_load_packet),
                &constant_load, &error) &&
                constant_load.bank == shift::xbox::CapturedConstantBank::Alu &&
                constant_load.guest_address == 0x09D568A0u &&
                constant_load.start_index == 0x3F0u &&
                constant_load.dword_count == 16u &&
                constant_load.destination_register == 0x43F0u &&
                constant_load.byte_length == 64u,
            "captured PM4_LOAD_ALU_CONSTANT span decoded incorrectly");
    uint8_t constant_load_data[64]{};
    for (uint32_t i = 0; i < 16; ++i) write_be32(constant_load_data + i * 4, 0xA0u + i);
    std::vector<shift::xbox::GuestRegisterWrite> loaded_constants;
    require(shift::xbox::decode_captured_constant_load_data(
                constant_load, constant_load_data, sizeof(constant_load_data),
                &loaded_constants, &error) && loaded_constants.size() == 16u &&
                loaded_constants.front().register_index == 0x43F0u &&
                loaded_constants.front().value == 0xA0u &&
                loaded_constants.back().register_index == 0x43FFu &&
                loaded_constants.back().value == 0xAFu,
            "captured constant-load bytes were not mapped as big-endian register values");
    auto invalid_constant_load = std::vector<uint8_t>(
        captured_constant_load_packet,
        captured_constant_load_packet + sizeof(captured_constant_load_packet));
    invalid_constant_load[9] = 0x05;
    const auto unchanged_constant_load = constant_load;
    require(!shift::xbox::decode_captured_constant_load(
                invalid_constant_load.data(), invalid_constant_load.size(),
                &constant_load, &error) &&
                constant_load.guest_address == unchanged_constant_load.guest_address &&
                constant_load.destination_register == unchanged_constant_load.destination_register,
            "unsupported constant-load bank changed decoded output");
    shift::xbox::DecodedIndexedDraw framed_draw{};
    require(shift::xbox::decode_captured_draw_indx(
                framed_stream + packet_spans[4].byte_offset,
                packet_spans[4].byte_length, &framed_draw, &error),
            "framed DRAW_INDX did not reach the bounded draw decoder");

    std::vector<shift::xbox::PacketSpan> unchanged_spans = packet_spans;
    require(!shift::xbox::scan_captured_packet_stream(
                framed_stream, sizeof(framed_stream) - 1, &packet_spans, &error),
            "unaligned PM4 stream was accepted");
    require(packet_spans.size() == unchanged_spans.size(),
            "failed PM4 scan partially replaced its output");
    require(!shift::xbox::scan_captured_packet_stream(
                framed_stream, sizeof(framed_stream) - 4, &packet_spans, &error),
            "truncated PM4 packet stream was accepted");
    require(packet_spans.size() == unchanged_spans.size(),
            "truncated PM4 scan partially replaced its output");

    shift::xbox::DecodedIndexedDraw input{};
    require(shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket), &input, &error),
            "captured retail packet was rejected");
    const uint8_t captured_draw_indx_2[] = {
        0xC0, 0x02, 0x36, 0x00,
        0x00, 0x06, 0x00, 0x04,
        0x09, 0x75, 0xD7, 0xB0,
        0x40, 0x00, 0x00, 0x06,
    };
    shift::xbox::DecodedIndexedDraw draw_indx_2{};
    require(shift::xbox::decode_captured_draw_indx(
                captured_draw_indx_2, sizeof(captured_draw_indx_2),
                &draw_indx_2, &error) &&
                draw_indx_2.topology == input.topology &&
                draw_indx_2.index_count == input.index_count &&
                draw_indx_2.index_guest_address == input.index_guest_address &&
                draw_indx_2.index_byte_length == input.index_byte_length,
            "captured PM4_DRAW_INDX_2 DMA form decoded differently from DRAW_INDX");
    const uint8_t live_autoindex_point[] = {
        0xC0, 0x00, 0x36, 0x00, 0x00, 0x01, 0x00, 0x81,
    };
    require(shift::xbox::decode_captured_draw_indx(
                live_autoindex_point, sizeof(live_autoindex_point),
                &draw_indx_2, &error) && draw_indx_2.auto_index &&
                draw_indx_2.topology == shift::xbox::PrimitiveTopology::PointList &&
                draw_indx_2.index_count == 1,
            "live AutoIndex point packet was not decoded");
    const uint8_t live_autoindex_rectangle_list[] = {
        0xC0, 0x00, 0x36, 0x01, 0x00, 0x03, 0x00, 0x88,
    };
    require(shift::xbox::decode_captured_draw_indx(
                live_autoindex_rectangle_list,
                sizeof(live_autoindex_rectangle_list), &draw_indx_2, &error) &&
                draw_indx_2.auto_index &&
                draw_indx_2.topology ==
                    shift::xbox::PrimitiveTopology::RectangleList &&
                draw_indx_2.index_count == 3,
            "live AutoIndex rectangle-list packet was not decoded");
    auto captured_auto_index_draw = std::vector<uint8_t>(
        captured_draw_indx_2,
        captured_draw_indx_2 + sizeof(captured_draw_indx_2));
    captured_auto_index_draw[7] = 0x84;
    require(!shift::xbox::decode_captured_draw_indx(
                captured_auto_index_draw.data(),
                captured_auto_index_draw.size(), &draw_indx_2, &error) &&
                error == "unsupported AutoIndex DRAW_INDX_2 form",
            "non-indexed DRAW_INDX_2 auto-index form was accepted as an "
            "indexed draw");
    require(!shift::xbox::decode_captured_draw_indx(
                captured_draw_indx_2, sizeof(captured_draw_indx_2) - 4u,
                &draw_indx_2, &error),
            "truncated PM4_DRAW_INDX_2 packet was accepted");
    require(input.topology == shift::xbox::PrimitiveTopology::TriangleList,
            "primitive topology changed");
    require(input.index_count == 6, "index count changed");
    require(input.index_guest_address == 0x0975D7B0u, "index base changed");
    require(input.index_type_bits == 16, "index type changed");
    require(input.index_endian_mode == 1, "index endian mode changed");
    require(input.index_byte_length == 12, "index range changed");

    const uint32_t captured_vertex_descriptor[] = {0x0975DFD3u, 0x10000032u};
    shift::xbox::CapturedVertexFetch vertex_fetch{};
    require(shift::xbox::decode_captured_vertex_fetch(
                captured_vertex_descriptor, &vertex_fetch, &error),
            "captured vertex-fetch descriptor was rejected");
    require(vertex_fetch.guest_address == 0x0975DFD0u,
            "captured vertex-fetch address changed");
    require(vertex_fetch.endian_mode == 2 && vertex_fetch.size_words == 12 &&
                vertex_fetch.byte_length == 48,
            "captured vertex-fetch shape changed");

    const uint32_t captured_texture_descriptor[] = {
        0x8800D8FEu, 0x09D57086u, 0x001FE3FFu,
        0x01280C14u, 0x00000003u, 0x00000A10u,
    };
    shift::xbox::CapturedTextureFetch texture_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_texture_descriptor, &texture_fetch, &error),
            "captured texture-fetch descriptor was rejected");
    require(texture_fetch.guest_address == 0x09D57000u && texture_fetch.format == 6 &&
                texture_fetch.endian_mode == 2,
            "captured texture resource identity changed");
    require(texture_fetch.width == 1024 && texture_fetch.height == 256 &&
                texture_fetch.pitch == 1024 &&
                texture_fetch.byte_length == 1024u * 256u * 4u && texture_fetch.tiled,
            "captured texture dimensions or layout changed");
    require(texture_fetch.dimension == 1 && texture_fetch.swizzle == 0x60Au &&
                texture_fetch.mag_filter == 1 && texture_fetch.min_filter == 1 &&
                texture_fetch.mip_filter == 2 && texture_fetch.aniso_filter == 0,
            "captured texture sampling fields changed");
    require(texture_fetch.sign_x == 3 && texture_fetch.sign_y == 3 &&
                texture_fetch.sign_z == 3 && texture_fetch.sign_w == 0 &&
                texture_fetch.clamp_x == 6 && texture_fetch.clamp_y == 6 &&
                texture_fetch.clamp_z == 0 && !texture_fetch.integer_format &&
                texture_fetch.border_color == 0 && !texture_fetch.border_size,
            "captured texture channel or clamp state changed");

    shift::xbox::CapturedTextureSampling texture_sampling{};
    require(shift::xbox::decode_captured_texture_sampling(
                texture_fetch, &texture_sampling, &error),
            "captured texture sampling state was rejected");
    require(texture_sampling.swizzle == std::array<shift::xbox::TextureComponent, 4>{
                shift::xbox::TextureComponent::Z,
                shift::xbox::TextureComponent::Y,
                shift::xbox::TextureComponent::X,
                shift::xbox::TextureComponent::W},
            "captured texture swizzle selectors changed");
    require(texture_sampling.signs == std::array<shift::xbox::TextureSign, 4>{
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Unsigned},
            "captured texture channel encodings changed");
    require(texture_sampling.clamps == std::array<shift::xbox::TextureClamp, 3>{
                shift::xbox::TextureClamp::ClampToBorder,
                shift::xbox::TextureClamp::ClampToBorder,
                shift::xbox::TextureClamp::Repeat},
            "captured texture clamp modes changed");
    require(texture_sampling.mag_filter == shift::xbox::TextureFilter::Linear &&
                texture_sampling.min_filter == shift::xbox::TextureFilter::Linear &&
                texture_sampling.mip_filter == shift::xbox::TextureFilter::BaseMap &&
                texture_sampling.anisotropy == shift::xbox::TextureAnisotropy::Disabled &&
                texture_sampling.border_color == shift::xbox::TextureBorderColor::AbgrBlack &&
                !texture_sampling.border_alpha_known,
            "captured texture sampler interpretation changed");

    const shift::xbox::CapturedRasterRegisters captured_raster_registers{
        0x14000500u, 0x00010000u, 0x000002D0u, 0x00000004u,
        0x00700770u, 0x0000000Fu, 0x44200000u, 0x44200000u,
        0xC3B40000u, 0x43B40000u, 0x00000000u, 0x20002000u,
        0x00000000u, 0x00000000u, 0x02D00500u, 0x07010706u,
    };
    shift::xbox::CapturedRasterState raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                captured_raster_registers, &raster_state, &error),
            "captured Xbox target and raster state was rejected");
    require(raster_state.width == 1280 && raster_state.height == 720 &&
                raster_state.surface_pitch == 1280 &&
                raster_state.sample_count == 1 && raster_state.color_base_tiles == 0 &&
                raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgba8Gamma &&
                raster_state.depth_base_tiles == 720 &&
                raster_state.depth_format ==
                    shift::xbox::CapturedDepthTargetFormat::D24S8,
            "captured Xbox render target interpretation changed");
    require(raster_state.color_write_mask == 0xFu && raster_state.viewport_y_flipped &&
                !raster_state.depth_test_enabled && !raster_state.depth_write_enabled &&
                !raster_state.stencil_test_enabled &&
                raster_state.blend_control_0 == 0x07010706u,
            "captured Xbox depth or color write state changed");
    require(raster_state.scissor_x0 == 0 && raster_state.scissor_y0 == 0 &&
                raster_state.scissor_x1 == 1280 && raster_state.scissor_y1 == 720 &&
                raster_state.scissor_has_area,
            "captured Xbox scissor bounds changed");

    shift::xbox::CapturedRasterRegisters live_raster_registers{
        0x0A020280u, 0x00010000u, 0x000002D0u, 0x00000004u,
        0x00008777u, 0x0000FFFFu, 0x44200000u, 0x44200000u,
        0xC3B40000u, 0x43B40000u, 0x00000000u, 0x20002000u,
        0x00000000u, 0x00000000u, 0x20002000u, 0x00010001u,
    };
    shift::xbox::CapturedRasterState live_raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.width == 1280 &&
                live_raster_state.height == 720 &&
                live_raster_state.surface_pitch == 640 &&
                live_raster_state.sample_count == 4 &&
                live_raster_state.color_write_mask == 0xFu &&
                live_raster_state.depth_test_enabled &&
                live_raster_state.depth_write_enabled &&
                live_raster_state.stencil_test_enabled &&
                live_raster_state.blend_control_0 == 0x00010001u,
            "live 4x-MSAA raster contract was rejected");

    auto no_effect_raster = live_raster_state;
    no_effect_raster.color_write_mask = 0;
    no_effect_raster.depth_test_enabled = false;
    no_effect_raster.depth_write_enabled = false;
    no_effect_raster.stencil_test_enabled = false;
    require(shift::xbox::captured_draw_has_no_framebuffer_effects(no_effect_raster),
            "zero-write captured raster state was not identified as a no-op");
    no_effect_raster.depth_write_enabled = true;
    require(!shift::xbox::captured_draw_has_no_framebuffer_effects(no_effect_raster),
            "depth-writing captured draw was incorrectly identified as a no-op");

    live_raster_registers.color_info = 0x00000000u;
    require(shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error) &&
                live_raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgba8Linear,
            "captured linear RGBA8 Xenos color target was rejected");
    live_raster_registers.color_info = 0x00020000u;
    require(!shift::xbox::decode_captured_raster_state(
                live_raster_registers, &live_raster_state, &error),
            "unsupported Xenos color target format was accepted");

    shift::xbox::GuestRasterRegisterState raster_register_state;
    shift::xbox::CapturedRasterRegisters tracked_raster_registers{};
    require(!raster_register_state.snapshot(&tracked_raster_registers, &error),
            "incomplete raster register state was accepted");
    const std::array<shift::xbox::GuestRegisterWrite, 20> raster_writes{{
        {0x2000, captured_raster_registers.surface_info},
        {0x2001, captured_raster_registers.color_info},
        {0x2002, captured_raster_registers.depth_info},
        {0x2208, captured_raster_registers.mode_control},
        {0x2200, captured_raster_registers.depth_control},
        {0x2104, captured_raster_registers.color_mask},
        {0x210F, captured_raster_registers.viewport_x_scale},
        {0x2110, captured_raster_registers.viewport_x_offset},
        {0x2111, captured_raster_registers.viewport_y_scale},
        {0x2112, captured_raster_registers.viewport_y_offset},
        {0x200E, captured_raster_registers.screen_scissor_tl},
        {0x200F, captured_raster_registers.screen_scissor_br},
        {0x2080, captured_raster_registers.window_offset},
        {0x2081, captured_raster_registers.window_scissor_tl},
        {0x2082, captured_raster_registers.window_scissor_br},
        {0x2201, captured_raster_registers.blend_control_0},
        {0x2318, 0x00100004u},
        {0x2319, 0x0975E000u},
        {0x231A, 0x02D00500u},
        {0x231B, 0x00000306u},
    }};
    for (const auto& write : raster_writes) raster_register_state.apply(write);
    raster_register_state.apply({0x3000, 0xFFFFFFFFu});
    require(raster_register_state.snapshot(&tracked_raster_registers, &error),
            "captured PM4 raster register writes did not produce complete state");
    require(tracked_raster_registers.copy_valid_mask == 0xFu &&
                tracked_raster_registers.copy_control == 0x00100004u &&
                tracked_raster_registers.copy_dest_base == 0x0975E000u &&
                tracked_raster_registers.copy_dest_pitch == 0x02D00500u &&
                tracked_raster_registers.copy_dest_info == 0x00000306u,
            "captured Xenos EDRAM copy registers changed");
    shift::xbox::CapturedRasterState tracked_raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                tracked_raster_registers, &tracked_raster_state, &error) &&
                tracked_raster_state.width == raster_state.width &&
                tracked_raster_state.height == raster_state.height &&
                tracked_raster_state.scissor_x1 == raster_state.scissor_x1 &&
                tracked_raster_state.depth_format == raster_state.depth_format,
            "tracked PM4 raster state diverged from the captured draw contract");
    raster_register_state.reset();
    require(!raster_register_state.snapshot(&tracked_raster_registers, &error),
            "reset raster register state retained stale draw state");

    shift::xbox::CapturedRasterRegisters unsupported_raster = captured_raster_registers;
    unsupported_raster.window_offset = 1;
    require(!shift::xbox::decode_captured_raster_state(
                unsupported_raster, &raster_state, &error),
            "uncaptured non-zero window offset was accepted");

    std::array<uint32_t, 512 * 4> captured_float_constants{};
    const auto set_float4 = [&](uint32_t index, std::array<uint32_t, 4> value) {
        std::copy(value.begin(), value.end(), captured_float_constants.begin() + index * 4);
    };
    set_float4(0, {0x43B14000u, 0, 0, 0x44200000u});
    set_float4(1, {0, 0x42B00000u, 0, 0x43B3C000u});
    set_float4(2, {0, 0, 0x3F800000u, 0});
    set_float4(3, {0, 0, 0, 0x3F800000u});
    set_float4(64, {0x3F47FFFFu, 0x00000000u, 0x00000000u, 0xC3F9FFFFu});
    set_float4(65, {0x00000000u, 0x3FB1C71Cu, 0x00000000u, 0xC3F9FFFFu});
    set_float4(66, {0x00000000u, 0x00000000u, 0x3F8020C5u, 0xBF8020C5u});
    set_float4(67, {0x00000000u, 0x00000000u, 0x3F800000u, 0x00000000u});
    set_float4(68, {0x3EB14000u, 0x00000000u, 0x00000000u, 0x3EB14000u});
    set_float4(69, {0x00000000u, 0x3EB00000u, 0x00000000u, 0x3EB00000u});
    set_float4(254, {0x00000000u, 0x3F800000u, 0xBF800000u, 0x40800000u});
    set_float4(255, {0x43FA0000u, 0x00000000u, 0x00000000u, 0x00000000u});
    set_float4(256, {0x3F800000u, 0x3F800000u, 0x3F800000u, 0x3F800000u});
    set_float4(511, {0x3F800000u, 0x00000000u, 0x00000000u, 0x00000000u});
    std::array<uint32_t, 8> captured_bool_constants{};
    captured_bool_constants[4] = 0x00000001u;
    shift::xbox::CapturedShaderConstants shader_constants{};
    require(shift::xbox::decode_captured_shader_constants(
                captured_float_constants.data(), captured_float_constants.size(),
                captured_bool_constants.data(), captured_bool_constants.size(),
                0x000FF000u, 0x000FF100u, &shader_constants, &error),
            "captured Xbox shader constant banks were rejected");
    require(shader_constants.vertex_float_constants[0] ==
                std::array<uint32_t, 4>{0x43B14000u, 0, 0, 0x44200000u} &&
                shader_constants.vertex_float_constants[1] ==
                std::array<uint32_t, 4>{0, 0x42B00000u, 0, 0x43B3C000u} &&
                shader_constants.vertex_float_constants[2][2] == 0x3F800000u &&
                shader_constants.vertex_float_constants[3][3] == 0x3F800000u &&
                shader_constants.vertex_float_constants[64][0] == 0x3F47FFFFu &&
                shader_constants.vertex_float_constants[69][3] == 0x3EB00000u &&
                shader_constants.vertex_float_constants[254][2] == 0xBF800000u &&
                shader_constants.vertex_float_constants[255][0] == 0x43FA0000u,
            "captured Xbox vertex shader constants changed");
    require(shader_constants.pixel_float_constants[0] ==
                std::array<uint32_t, 4>{0x3F800000u, 0x3F800000u,
                                        0x3F800000u, 0x3F800000u} &&
                shader_constants.pixel_float_constants[255] ==
                std::array<uint32_t, 4>{0x3F800000u, 0, 0, 0} &&
                shader_constants.pixel_b128 && !shader_constants.pixel_b129 &&
                shader_constants.pixel_boolean_constants_valid,
            "captured Xbox pixel constants or conditional path changed");
    shift::xbox::CapturedXboxShaderRegisterState shader_register_state;
    shift::xbox::CapturedShaderConstants tracked_shader_constants{};
    std::array<uint32_t, 2> tracked_vertex_descriptor{};
    std::array<uint32_t, 6> tracked_texture_descriptor{};
    require(!shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error) &&
                error == "missing vertex shader control register 0x2307",
            "incomplete captured shader register state was accepted");
    shader_register_state.apply({0x2307u, 0x000FF000u});
    shader_register_state.apply({0x2308u, 0x000FF100u});
    const std::array<uint32_t, 10> required_shader_constants{
        64u, 65u, 66u, 67u, 68u, 69u, 254u, 255u, 256u, 511u,
    };
    for (uint32_t c : required_shader_constants) {
        for (uint32_t component = 0; component < 4; ++component) {
            shader_register_state.apply({
                0x4000u + c * 4u + component,
                captured_float_constants[c * 4u + component],
            });
        }
    }
    for (uint32_t i = 0; i < 6; ++i) {
        shader_register_state.apply({0x4800u + i, captured_texture_descriptor[i]});
    }
    for (uint32_t i = 0; i < 2; ++i) {
        shader_register_state.apply({0x4800u + 190u + i, captured_vertex_descriptor[i]});
    }
    require(shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error) &&
                !tracked_shader_constants.pixel_boolean_constants_valid &&
                !tracked_shader_constants.pixel_b128 &&
                !tracked_shader_constants.pixel_b129,
            "unloaded pixel boolean constants were not marked as unknown");
    shader_register_state.apply({0x4904u, captured_bool_constants[4]});
    require(shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error) &&
                tracked_shader_constants.vertex_float_constants[64][0] == 0x3F47FFFFu &&
                tracked_shader_constants.pixel_float_constants[255][0] == 0x3F800000u &&
                tracked_shader_constants.pixel_b128 &&
                tracked_vertex_descriptor ==
                    std::array<uint32_t, 2>{0x0975DFD3u, 0x10000032u} &&
                tracked_texture_descriptor ==
                    std::array<uint32_t, 6>{0x8800D8FEu, 0x09D57086u, 0x001FE3FFu,
                                            0x01280C14u, 0x00000003u, 0x00000A10u},
            "captured shader register bank snapshot diverged from its draw inputs");
    shader_register_state.reset();
    require(!shader_register_state.snapshot(
                &tracked_shader_constants, &tracked_vertex_descriptor,
                &tracked_texture_descriptor, &error),
            "shader register reset retained captured draw state");
    shift::xbox::CapturedXboxShaderRegisterState dynamic_fetch_state;
    dynamic_fetch_state.apply({0x4800u, captured_vertex_descriptor[0]});
    dynamic_fetch_state.apply({0x4801u, captured_vertex_descriptor[1]});
    std::array<uint32_t, 2> descriptor_zero{};
    require(dynamic_fetch_state.snapshot_vertex_fetch_descriptor(
                0, &descriptor_zero, &error) &&
                descriptor_zero == std::array<uint32_t, 2>{
                    captured_vertex_descriptor[0], captured_vertex_descriptor[1]},
            "shader fetch descriptor zero was not dynamically addressable");
    require(!dynamic_fetch_state.snapshot_vertex_fetch_descriptor(
                96, &descriptor_zero, &error),
            "out-of-range vertex fetch descriptor index was accepted");
    shift::xbox::CapturedXboxShaderRegisterState sparse_constants;
    sparse_constants.apply({0x2307u, 0x000FF000u});
    sparse_constants.apply({0x2308u, 0x000FF100u});
    shift::xbox::CapturedShaderConstants sparse_snapshot{};
    require(sparse_constants.snapshot_constants(&sparse_snapshot, &error) &&
                !sparse_constants.validate_float_constants(
                    shift::xbox::GuestShaderStage::Vertex,
                    std::vector<uint32_t>{0}, false, &error) &&
                error == "captured vertex float constant 0 is incomplete",
            "shader constant snapshot still requires unused fixed registers");
    for (uint32_t component = 0; component < 4; ++component) {
        sparse_constants.apply({0x4000u + component, 0x3F800000u});
    }
    require(sparse_constants.validate_float_constants(
                shift::xbox::GuestShaderStage::Vertex,
                std::vector<uint32_t>{0}, false, &error),
            "captured shader read-set constant validation rejected a loaded register");
    require(!shift::xbox::decode_captured_shader_constants(
                captured_float_constants.data(), captured_float_constants.size() - 1,
                captured_bool_constants.data(), captured_bool_constants.size(),
                0x000FF000u, 0x000FF100u, &shader_constants, &error),
            "truncated captured shader constant bank was accepted");
    require(!shift::xbox::decode_captured_shader_constants(
                captured_float_constants.data(), captured_float_constants.size(),
                captured_bool_constants.data(), captured_bool_constants.size(),
                0x000FF000u, 0x000FE100u, &shader_constants, &error),
            "shader constant range too short for the captured pair was accepted");

    shift::xbox::CapturedTextureFetch white_border_texture = texture_fetch;
    white_border_texture.border_color = 1;
    require(shift::xbox::decode_captured_texture_sampling(
                white_border_texture, &texture_sampling, &error) &&
                texture_sampling.border_color == shift::xbox::TextureBorderColor::AbgrWhite &&
                texture_sampling.border_alpha_known,
            "known opaque-white border color lost its alpha contract");
    shift::xbox::CapturedTextureFetch reserved_swizzle = texture_fetch;
    reserved_swizzle.swizzle = (reserved_swizzle.swizzle & ~0x7u) | 6u;
    require(!shift::xbox::decode_captured_texture_sampling(
                reserved_swizzle, &texture_sampling, &error),
            "reserved texture swizzle selector was accepted");
    shift::xbox::CapturedTextureFetch reserved_anisotropy = texture_fetch;
    reserved_anisotropy.aniso_filter = 6;
    require(!shift::xbox::decode_captured_texture_sampling(
                reserved_anisotropy, &texture_sampling, &error),
            "reserved texture anisotropy value was accepted");

    std::vector<uint8_t> tiled_texture(texture_fetch.byte_length);
    const size_t texture_pixels = texture_fetch.byte_length / 4;
    for (size_t pixel = 0; pixel < texture_pixels; ++pixel) {
        tiled_texture[pixel * 4] = static_cast<uint8_t>(pixel);
        tiled_texture[pixel * 4 + 1] = static_cast<uint8_t>(pixel >> 8);
        tiled_texture[pixel * 4 + 2] = static_cast<uint8_t>(pixel >> 16);
        tiled_texture[pixel * 4 + 3] = static_cast<uint8_t>(pixel >> 24);
    }
    std::vector<uint8_t> linear_texture;
    require(shift::xbox::untile_captured_texture_2d(
                texture_fetch, tiled_texture.data(), tiled_texture.size(),
                &linear_texture, &error),
            "captured tiled texture bytes were rejected");
    require(linear_texture.size() == texture_fetch.byte_length,
            "untiled texture byte length changed");

    std::vector<bool> seen_texture_pixels(texture_pixels, false);
    for (size_t pixel = 0; pixel < texture_pixels; ++pixel) {
        const uint32_t source_pixel = read_be32(linear_texture.data() + pixel * 4);
        require(source_pixel < texture_pixels && !seen_texture_pixels[source_pixel],
                "untile mapping duplicated or exceeded a source texel");
        seen_texture_pixels[source_pixel] = true;
    }
    for (bool seen : seen_texture_pixels) {
        require(seen, "untile mapping skipped a source texel");
    }
    const auto require_texture_source_pixel = [&](uint32_t x, uint32_t y,
                                                  uint32_t expected) {
        const size_t pixel = static_cast<size_t>(y) * texture_fetch.width + x;
        require(read_be32(linear_texture.data() + pixel * 4) == expected,
                "captured Xenos tiled address or 8-in-32 byte order changed");
    };
    require_texture_source_pixel(0, 0, 0);
    require_texture_source_pixel(4, 0, 8);
    require_texture_source_pixel(0, 2, 64);
    require_texture_source_pixel(0, 16, 512);
    require_texture_source_pixel(32, 0, 1024);
    require_texture_source_pixel(0, 32, 32768);
    require_texture_source_pixel(1023, 255, 262111);

    shift::xbox::CapturedTextureFetch unsupported_texture_layout = texture_fetch;
    unsupported_texture_layout.pitch -= 32;
    require(!shift::xbox::untile_captured_texture_2d(
                unsupported_texture_layout, tiled_texture.data(), tiled_texture.size(),
                &linear_texture, &error),
            "uncaptured texture pitch was accepted");
    require(!shift::xbox::untile_captured_texture_2d(
                texture_fetch, tiled_texture.data(), tiled_texture.size() - 1,
                &linear_texture, &error),
            "truncated captured texture was accepted");

    const uint8_t captured_indices[] = {
        0x00, 0x00, 0x00, 0x01, 0x00, 0x02,
        0x00, 0x02, 0x00, 0x01, 0x00, 0x03,
    };
    const std::vector<uint8_t> expected_vk_indices{
        0x00, 0x00, 0x01, 0x00, 0x02, 0x00,
        0x02, 0x00, 0x01, 0x00, 0x03, 0x00,
    };
    std::vector<uint8_t> normalized;
    require(shift::xbox::normalize_captured_buffer_bytes(
                input.index_endian_mode, captured_indices, sizeof(captured_indices),
                &normalized, &error),
            "captured 8-in-16 index bytes were rejected");
    require(normalized == expected_vk_indices,
            "captured index bytes did not normalize to Vulkan UInt16 values");
    uint32_t maximum_vertex_index = 0;
    require(shift::xbox::decode_captured_index_data(
                input, captured_indices, sizeof(captured_indices), &normalized,
                &maximum_vertex_index, &error) &&
                normalized == expected_vk_indices && maximum_vertex_index == 3,
            "captured index data did not resolve the highest referenced vertex");
    uint32_t vertex_span_bytes = 0;
    require(shift::xbox::captured_vertex_required_bytes(
                maximum_vertex_index, 12, 0, 12, &vertex_span_bytes, &error) &&
                vertex_span_bytes == 48,
            "captured FLOAT3 vertex span did not cover four 12-byte vertices");
    require(!shift::xbox::captured_vertex_required_bytes(
                std::numeric_limits<uint32_t>::max(), 12, 0, 12,
                &vertex_span_bytes, &error),
            "overflowing captured vertex span was accepted");

    const uint8_t captured_vertex_words[] = {
        0xBF, 0x80, 0x00, 0x00, 0xBF, 0x80, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
    };
    const std::vector<uint8_t> expected_vk_vertex_words{
        0x00, 0x00, 0x80, 0xBF, 0x00, 0x00, 0x80, 0xBF,
        0x00, 0x00, 0x00, 0x00,
    };
    require(shift::xbox::normalize_captured_buffer_bytes(
                vertex_fetch.endian_mode, captured_vertex_words,
                sizeof(captured_vertex_words),
                &normalized, &error),
            "captured 8-in-32 vertex words were rejected");
    require(normalized == expected_vk_vertex_words,
            "captured vertex words did not normalize to Vulkan float32 values");

    require(!shift::xbox::normalize_captured_buffer_bytes(
                3, captured_indices, sizeof(captured_indices), &normalized, &error),
            "uncaptured endian mode was accepted");
    require(!shift::xbox::normalize_captured_buffer_bytes(
                1, captured_indices, sizeof(captured_indices) - 1, &normalized, &error),
            "truncated 8-in-16 resource was accepted");

    uint32_t unsupported_vertex_descriptor[] = {
        captured_vertex_descriptor[0], captured_vertex_descriptor[1]};
    unsupported_vertex_descriptor[0] =
        (unsupported_vertex_descriptor[0] & 0xFFFFFFFCu) | 2u;
    require(!shift::xbox::decode_captured_vertex_fetch(
                unsupported_vertex_descriptor, &vertex_fetch, &error),
            "texture-fetch descriptor was accepted as a vertex buffer");

    uint32_t unsupported_texture_descriptor[6];
    for (size_t i = 0; i < 6; ++i) {
        unsupported_texture_descriptor[i] = captured_texture_descriptor[i];
    }
    unsupported_texture_descriptor[1] =
        (unsupported_texture_descriptor[1] & ~0x3Fu) | 5u;
    require(!shift::xbox::decode_captured_texture_fetch(
                unsupported_texture_descriptor, &texture_fetch, &error),
            "uncaptured texture format was accepted");

    uint8_t unsupported[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported[i] = kCapturedPacket[i];
    }
    unsupported[2] = 0x23;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported, sizeof(unsupported), &input, &error),
            "unsupported packet opcode was accepted");

    uint8_t disagreeing_counts[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        disagreeing_counts[i] = kCapturedPacket[i];
    }
    disagreeing_counts[9] = 0x07;
    require(!shift::xbox::decode_captured_draw_indx(
                disagreeing_counts, sizeof(disagreeing_counts), &input, &error),
            "disagreeing packet index counts were accepted");

    uint8_t unsupported_index_size[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_index_size[i] = kCapturedPacket[i];
    }
    unsupported_index_size[10] |= 0x08;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_index_size, sizeof(unsupported_index_size), &input, &error),
            "unsupported 32-bit index format was accepted");

    uint8_t unsupported_source[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_source[i] = kCapturedPacket[i];
    }
    unsupported_source[11] |= 0x40;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_source, sizeof(unsupported_source), &input, &error),
            "unsupported immediate-index source was accepted");

    uint8_t unsupported_endian[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_endian[i] = kCapturedPacket[i];
    }
    unsupported_endian[16] = 0x80;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_endian, sizeof(unsupported_endian), &input, &error),
            "uncaptured index endian mode was accepted");

    require(!shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket) - 4, &input, &error),
            "truncated packet was accepted");

    const uint8_t captured_swap[] = {
        0xC0, 0x03, 0x64, 0x00,  // PM4_XE_SWAP, four payload dwords
        0x53, 0x57, 0x41, 0x50,  // "SWAP"
        0x09, 0x75, 0xD0, 0x00,  // 4 KiB-aligned physical frontbuffer
        0x00, 0x00, 0x05, 0x00,  // 1280
        0x00, 0x00, 0x02, 0xD0,  // 720
    };
    shift::xbox::DecodedGuestSwap swap{};
    require(shift::xbox::decode_guest_swap(
                captured_swap, sizeof(captured_swap), &swap, &error),
            "captured PM4_XE_SWAP packet was rejected");
    require(swap.frontbuffer_guest_address == 0x0975D000u &&
                swap.width == 1280u && swap.height == 720u,
            "PM4_XE_SWAP fields were decoded incorrectly");
    uint8_t bad_swap[sizeof(captured_swap)];
    std::copy(std::begin(captured_swap), std::end(captured_swap), std::begin(bad_swap));
    bad_swap[4] = 0;
    require(!shift::xbox::decode_guest_swap(
                bad_swap, sizeof(bad_swap), &swap, &error),
            "PM4_XE_SWAP with an invalid signature was accepted");
    require(!shift::xbox::decode_guest_swap(
                captured_swap, sizeof(captured_swap) - 4, &swap, &error),
            "truncated PM4_XE_SWAP packet was accepted");

    std::cout << "captured PM4_DRAW_INDX input check passed\n";
    return 0;
}
