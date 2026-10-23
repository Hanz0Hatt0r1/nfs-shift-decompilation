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
    return 0;
}
