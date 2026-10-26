#include "shift_xbox_guest_ring.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

constexpr std::array<uint8_t, 20> kCapturedDrawPacket = {
    0xC0, 0x03, 0x22, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x00, 0x04, 0x09, 0x75, 0xD7, 0xB0,
    0x40, 0x00, 0x00, 0x06,
};

constexpr std::array<uint8_t, 12> kCapturedIndirectBufferPacket = {
    0xC0, 0x01, 0x3F, 0x00, 0x09, 0x75, 0xB6, 0x60,
    0x00, 0x00, 0x00, 0x4A,
};
constexpr std::array<uint8_t, 8> kCapturedInterruptPacket = {
    0xC0, 0x00, 0x54, 0x00, 0x00, 0x00, 0x00, 0x24,
};
// First 30 dwords of the retail callback-stream capture. The capture continues
// with another packet at dword 30; this fixture ends after the complete
// CALLBACK_ACK write at dword 29.
constexpr std::array<uint32_t, 30> kCapturedCallbackWaitAckPrefix = {
    0x00000100, 0x000005C8, 0x00020000, 0x0001057C, 0x823A4758,
    0x00000208, 0x00000578, 0x00000004, 0xC0043C00, 0x00000013,
    0x1B964002, 0x00000004, 0xFFFFFFFF, 0x00000100, 0xC0043C00,
    0x00000013, 0x1B964016, 0x00000208, 0xFFFFFFFF, 0x00000100,
    0xC0043C00, 0x00000013, 0x1B964012, 0x823A4758, 0xFFFFFFFF,
    0x00000100, 0xC0005400, 0x00000004, 0x0000045E, 0x00000004,
};
constexpr std::array<uint8_t, 16> kCapturedEventWriteShdPacket = {
    0xC0, 0x02, 0x58, 0x00, 0x00, 0x00, 0x00, 0x03,
    0x17, 0xAF, 0x40, 0x06, 0xA9, 0x5D, 0x00, 0xE4,
};
constexpr std::array<uint8_t, 16> kCapturedEventWriteShdCounterPacket = {
    0xC0, 0x02, 0x58, 0x00, 0x80, 0x00, 0x00, 0x03,
    0x17, 0xAF, 0x40, 0x40, 0xDE, 0xAD, 0xBE, 0xEF,
};

struct GuestMemoryFixture {
    uint32_t guest_address = 0;
    std::vector<uint8_t> bytes;
    size_t available_bytes = 0;
};

bool read_guest_memory(
    void* context,
    uint32_t guest_address,
    size_t,
    const uint8_t** bytes,
    size_t* available_bytes) {
    auto* fixture = static_cast<GuestMemoryFixture*>(context);
    if (!fixture || !bytes || !available_bytes ||
        guest_address != fixture->guest_address) {
        return false;
    }
    *bytes = fixture->bytes.data();
    *available_bytes = fixture->available_bytes;
    return true;
}

}  // namespace

int main() {
    size_t ring_byte_length = 99u;
    std::string error;
    require(shift::xbox::guest_ring_byte_length_from_size_log2(
                0u, &ring_byte_length, &error) && ring_byte_length == 8u,
            "minimum ReXGlue ring size was calculated incorrectly");
    require(shift::xbox::guest_ring_byte_length_from_size_log2(
                9u, &ring_byte_length, &error) && ring_byte_length == 4096u,
            "captured ReXGlue ring size was calculated incorrectly");
    require(shift::xbox::guest_ring_byte_length_from_size_log2(
                23u, &ring_byte_length, &error) && ring_byte_length == 64u * 1024u * 1024u,
            "maximum permitted ReXGlue ring size was calculated incorrectly");
    require(!shift::xbox::guest_ring_byte_length_from_size_log2(
                24u, &ring_byte_length, &error) &&
                ring_byte_length == 64u * 1024u * 1024u,
            "oversized ReXGlue ring size was accepted or changed output");
    require(!shift::xbox::guest_ring_byte_length_from_size_log2(
                UINT32_MAX, &ring_byte_length, &error),
            "overflowing ReXGlue ring size was accepted");

    std::array<uint8_t, 32> ring{};
    for (size_t i = 0; i < kCapturedDrawPacket.size(); ++i) {
        const size_t ring_index = (24u + i) % ring.size();
        ring[ring_index] = kCapturedDrawPacket[i];
    }

    shift::xbox::GuestRingBatch batch{};
    require(shift::xbox::snapshot_guest_ring_batch(
                ring.data(), ring.size(), 6, 3, &batch, &error),
            "captured DRAW_INDX spanning ring wrap was rejected");
    require(batch.bytes.size() == kCapturedDrawPacket.size() &&
                std::equal(batch.bytes.begin(), batch.bytes.end(),
                           kCapturedDrawPacket.begin()),
            "ring wrap copy changed the captured packet bytes");
    require(batch.packets.size() == 1 &&
                batch.packets[0].type == shift::xbox::PacketType::Type3 &&
                batch.packets[0].byte_offset == 0 &&
                batch.packets[0].byte_length == kCapturedDrawPacket.size() &&
                batch.packets[0].opcode == 0x22 &&
                batch.next_read_pointer_dwords == 3,
            "ring consumer did not frame the wrapped DRAW_INDX correctly");
    shift::xbox::DecodedIndexedDraw draw{};
    require(shift::xbox::decode_captured_draw_indx(
                batch.bytes.data() + batch.packets[0].byte_offset,
                batch.packets[0].byte_length, &draw, &error) &&
                draw.index_count == 6,
            "wrapped captured DRAW_INDX did not reach the bounded decoder");

    uint32_t interrupt_cpu_mask = 0;
    require(shift::xbox::decode_captured_gpu_interrupt(
                kCapturedInterruptPacket.data(), kCapturedInterruptPacket.size(),
                &interrupt_cpu_mask, &error) && interrupt_cpu_mask == 0x24u,
            "captured PM4_INTERRUPT CPU mask was not decoded in guest byte order");
    require(!shift::xbox::decode_captured_gpu_interrupt(
                kCapturedInterruptPacket.data(), kCapturedInterruptPacket.size() - 4u,
                &interrupt_cpu_mask, &error),
            "truncated PM4_INTERRUPT packet was accepted");

    std::array<uint8_t, 128> callback_ring{};
    for (size_t index = 0; index < kCapturedCallbackWaitAckPrefix.size(); ++index) {
        const uint32_t dword = kCapturedCallbackWaitAckPrefix[index];
        callback_ring[index * 4u] = static_cast<uint8_t>(dword >> 24);
        callback_ring[index * 4u + 1u] = static_cast<uint8_t>(dword >> 16);
        callback_ring[index * 4u + 2u] = static_cast<uint8_t>(dword >> 8);
        callback_ring[index * 4u + 3u] = static_cast<uint8_t>(dword);
    }
    shift::xbox::GuestRingBatch callback_batch{};
    require(shift::xbox::snapshot_guest_ring_batch(
                callback_ring.data(), callback_ring.size(), 0u,
                static_cast<uint32_t>(kCapturedCallbackWaitAckPrefix.size()),
                &callback_batch, &error) &&
                callback_batch.packets.size() == 8u &&
                callback_batch.bytes.size() == 30u * sizeof(uint32_t),
            "captured retail wait/interrupt/ack prefix did not frame into eight complete packets");

    const auto decode_callback_register_packet =
        [&callback_batch, &error](size_t packet_index,
                                 std::vector<shift::xbox::GuestRegisterWrite>* writes) {
            const auto& packet = callback_batch.packets[packet_index];
            return shift::xbox::decode_guest_register_writes(
                callback_batch.bytes.data() + packet.byte_offset,
                packet.byte_length, writes, &error);
        };
    std::vector<shift::xbox::GuestRegisterWrite> callback_register_writes;
    require(decode_callback_register_packet(1u, &callback_register_writes) &&
                callback_register_writes.size() == 3u &&
                callback_register_writes[0].register_index == 0u &&
                callback_register_writes[0].value == 0x0001057Cu &&
                callback_register_writes[1].register_index == 1u &&
                callback_register_writes[1].value == 0x823A4758u &&
                callback_register_writes[2].register_index == 2u &&
                callback_register_writes[2].value == 0x00000208u,
            "captured Type-0 packet was misread as a CALLBACK_ADDRESS/CONTEXT register write");
    require(decode_callback_register_packet(2u, &callback_register_writes) &&
                callback_register_writes.size() == 1u &&
                callback_register_writes[0].register_index == 0x0578u &&
                callback_register_writes[0].value == 4u,
            "captured interrupt-sync scratch register write was decoded incorrectly");

    const auto captured_dword = [&callback_batch](size_t dword_index) {
        const uint8_t* bytes = callback_batch.bytes.data() + dword_index * 4u;
        return (uint32_t(bytes[0]) << 24) | (uint32_t(bytes[1]) << 16) |
               (uint32_t(bytes[2]) << 8) | uint32_t(bytes[3]);
    };
    require(callback_batch.packets[3].type == shift::xbox::PacketType::Type3 &&
                callback_batch.packets[3].opcode == 0x3Cu &&
                callback_batch.packets[4].opcode == 0x3Cu &&
                callback_batch.packets[5].opcode == 0x3Cu &&
                captured_dword(23u) == 0x823A4758u,
            "captured callback value was not retained as the third WAIT_REG_MEM reference");
    require(callback_batch.packets[6].type == shift::xbox::PacketType::Type3 &&
                callback_batch.packets[6].opcode == 0x54u &&
                callback_batch.packets[6].byte_offset +
                        callback_batch.packets[6].byte_length ==
                    callback_batch.packets[7].byte_offset &&
                shift::xbox::decode_captured_gpu_interrupt(
                    callback_batch.bytes.data() + callback_batch.packets[6].byte_offset,
                    callback_batch.packets[6].byte_length, &interrupt_cpu_mask, &error) &&
                interrupt_cpu_mask == 4u,
            "captured PM4_INTERRUPT CPU mask or packet order changed");
    require(decode_callback_register_packet(7u, &callback_register_writes) &&
                callback_register_writes.size() == 1u &&
                callback_register_writes[0].register_index == 0x045Eu &&
                callback_register_writes[0].value == 4u,
            "captured CALLBACK_ACK register write was not decoded after PM4_INTERRUPT");

    shift::xbox::DecodedEventWriteShd event_write{};
    require(shift::xbox::decode_guest_event_write_shd(
                kCapturedEventWriteShdPacket.data(),
                kCapturedEventWriteShdPacket.size(), &event_write, &error) &&
                event_write.initiator == 3u &&
                event_write.guest_address == 0x17AF4004u &&
                event_write.endian_mode == 2u &&
                event_write.value == 0xA95D00E4u &&
                shift::xbox::event_write_shd_value(event_write, 9u) ==
                    0xA95D00E4u,
            "captured EVENT_WRITE_SHD guest address, endian mode, or value was decoded incorrectly");
    require(shift::xbox::decode_guest_event_write_shd(
                kCapturedEventWriteShdCounterPacket.data(),
                kCapturedEventWriteShdCounterPacket.size(), &event_write, &error) &&
                event_write.guest_address == 0x17AF4040u &&
                event_write.endian_mode == 0u &&
                event_write.value == 0xDEADBEEFu &&
                shift::xbox::event_write_shd_value(event_write, 9u) == 9u,
            "EVENT_WRITE_SHD counter initiator did not override the packet value");
    require(!shift::xbox::decode_guest_event_write_shd(
                kCapturedEventWriteShdPacket.data(),
                kCapturedEventWriteShdPacket.size() - 4u, &event_write, &error),
            "truncated EVENT_WRITE_SHD packet was accepted");

    shift::xbox::GuestRingBatch empty{};
    require(shift::xbox::snapshot_guest_ring_batch(
                ring.data(), ring.size(), 3, 3, &empty, &error) &&
                empty.bytes.empty() && empty.packets.empty() &&
                empty.next_read_pointer_dwords == 3,
            "equal guest ring pointers were not treated as empty");

    shift::xbox::GuestRingBatch unchanged{};
    unchanged.next_read_pointer_dwords = 7;
    require(!shift::xbox::snapshot_guest_ring_batch(
                ring.data(), ring.size(), 0, 3, &unchanged, &error) &&
                unchanged.next_read_pointer_dwords == 7,
            "truncated guest packet advanced or partially replaced the output");
    require(!shift::xbox::snapshot_guest_ring_batch(
                ring.data(), 24, 0, 1, &unchanged, &error),
            "non-power-of-two guest ring size was accepted");
    require(!shift::xbox::snapshot_guest_ring_batch(
                ring.data(), ring.size(), 0, 8, &unchanged, &error),
            "out-of-range guest ring pointer was accepted");

    shift::xbox::GuestRingBatch indirect_root{};
    indirect_root.bytes.assign(kCapturedIndirectBufferPacket.begin(),
                               kCapturedIndirectBufferPacket.end());
    GuestMemoryFixture indirect_memory{};
    indirect_memory.guest_address = 0x0975B660u;
    indirect_memory.bytes.resize(74u * sizeof(uint32_t));
    indirect_memory.available_bytes = indirect_memory.bytes.size();
    shift::xbox::ExpandedGuestCommandStream expanded{};
    require(shift::xbox::expand_guest_indirect_buffers(
                indirect_root, read_guest_memory, &indirect_memory,
                &expanded, &error) &&
                expanded.indirect_buffer_count == 1u &&
                expanded.indirect_buffer_bytes == 74u * sizeof(uint32_t) &&
                expanded.packets.size() == 75u &&
                expanded.packets.front().packet.opcode == 0x3Fu &&
                expanded.packets.front().nesting_depth == 0u &&
                expanded.packets[1].packet.type == shift::xbox::PacketType::ZeroNop &&
                expanded.packets[1].source_guest_address == 0x0975B660u &&
                expanded.packets[1].source_guest_buffer_byte_length ==
                    74u * sizeof(uint32_t) &&
                expanded.packets[1].nesting_depth == 1u,
            "captured indirect span was not expanded with its packet provenance");

    shift::xbox::ExpandedGuestCommandStream unchanged_expansion{};
    unchanged_expansion.indirect_buffer_count = 9u;
    indirect_memory.available_bytes = indirect_memory.bytes.size() - 4u;
    require(!shift::xbox::expand_guest_indirect_buffers(
                indirect_root, read_guest_memory, &indirect_memory,
                &unchanged_expansion, &error) &&
                unchanged_expansion.indirect_buffer_count == 9u &&
                unchanged_expansion.packets.empty(),
            "short guest-memory span partially changed expanded output");

    indirect_memory.available_bytes = indirect_memory.bytes.size();
    std::copy(kCapturedIndirectBufferPacket.begin(),
              kCapturedIndirectBufferPacket.end(), indirect_memory.bytes.begin());
    require(!shift::xbox::expand_guest_indirect_buffers(
                indirect_root, read_guest_memory, &indirect_memory,
                &unchanged_expansion, &error) &&
                unchanged_expansion.indirect_buffer_count == 9u &&
                unchanged_expansion.packets.empty(),
            "cyclic indirect buffer was accepted or partially changed output");

    constexpr std::array<uint8_t, 12> retail_completion_ib_call = {
        0xC0, 0x01, 0x3F, 0x00, 0x09, 0x69, 0x2C, 0xE0,
        0x00, 0x00, 0x00, 0x1C,
    };
    constexpr std::array<uint32_t, 28> retail_completion_ib_dwords = {
        0xC0006000, 0xFFFFFFFF, 0xC0006200, 0xFFFFFFFF,
        0xC0006100, 0x00000000, 0xC0006300, 0x00000000,
        0x00022080, 0x00000000, 0x00000000, 0x02D00500,
        0x000005C8, 0x00020000, 0x00000F01, 0x0000200E,
        0x000005C8, 0x00020000, 0xC0003B00, 0x00007FFF,
        0xC0025800, 0x00000003, 0x17AF4006, 0xA9692D24,
        0xC0025800, 0x00000003, 0x17AF4002, 0x00001089,
    };
    shift::xbox::GuestRingBatch retail_completion_root{};
    retail_completion_root.bytes.assign(retail_completion_ib_call.begin(),
                                         retail_completion_ib_call.end());
    GuestMemoryFixture retail_completion_memory{};
    retail_completion_memory.guest_address = 0x09692CE0u;
    retail_completion_memory.bytes.reserve(
        retail_completion_ib_dwords.size() * sizeof(uint32_t));
    for (const uint32_t dword : retail_completion_ib_dwords) {
        retail_completion_memory.bytes.push_back(static_cast<uint8_t>(dword >> 24));
        retail_completion_memory.bytes.push_back(static_cast<uint8_t>(dword >> 16));
        retail_completion_memory.bytes.push_back(static_cast<uint8_t>(dword >> 8));
        retail_completion_memory.bytes.push_back(static_cast<uint8_t>(dword));
    }
    retail_completion_memory.available_bytes =
        retail_completion_memory.bytes.size();
    shift::xbox::ExpandedGuestCommandStream retail_completion{};
    require(shift::xbox::expand_guest_indirect_buffers(
                retail_completion_root, read_guest_memory,
                &retail_completion_memory, &retail_completion, &error) &&
                retail_completion.indirect_buffer_count == 1u &&
                retail_completion.packets.size() == 12u,
            "captured retail completion IB was not expanded into PM4 packets");
    constexpr std::array<uint32_t, 2> retail_completion_addresses = {
        0x17AF4004u, 0x17AF4000u,
    };
    constexpr std::array<uint32_t, 2> retail_completion_values = {
        0xA9692D24u, 0x00001089u,
    };
    size_t retail_completion_event_index = 0;
    for (const shift::xbox::ResolvedGuestPacket& resolved :
         retail_completion.packets) {
        if (resolved.packet.type != shift::xbox::PacketType::Type3 ||
            resolved.packet.opcode != 0x58u) {
            continue;
        }
        require(resolved.source_guest_address == 0x09692CE0u &&
                    resolved.nesting_depth == 1u &&
                    retail_completion_event_index <
                        retail_completion_addresses.size(),
                "retail EVENT_WRITE_SHD lost its indirect-buffer provenance");
        shift::xbox::DecodedEventWriteShd completion_event{};
        require(shift::xbox::decode_guest_event_write_shd(
                    retail_completion_memory.bytes.data() +
                        resolved.packet.byte_offset,
                    resolved.packet.byte_length, &completion_event, &error) &&
                    completion_event.initiator == 3u &&
                    completion_event.guest_address ==
                        retail_completion_addresses[retail_completion_event_index] &&
                    completion_event.endian_mode == 2u &&
                    shift::xbox::event_write_shd_value(completion_event, 0x1234u) ==
                        retail_completion_values[retail_completion_event_index],
                "retail nested EVENT_WRITE_SHD address, endian mode, or value changed");
        ++retail_completion_event_index;
    }
    require(retail_completion_event_index == retail_completion_addresses.size(),
            "retail completion IB did not expose both nested EVENT_WRITE_SHD packets");
    return 0;
}
