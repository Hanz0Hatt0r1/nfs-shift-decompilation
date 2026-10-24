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
    return 0;
}
