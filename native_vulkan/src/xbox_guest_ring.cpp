#include "shift_xbox_guest_ring.hpp"

#include <algorithm>
#include <cstring>
#include <limits>
#include <utility>

namespace shift::xbox {
namespace {

bool fail(const char* message, std::string* error) {
    if (error) *error = message;
    return false;
}

}  // namespace

bool snapshot_guest_ring_batch(
    const uint8_t* ring_bytes,
    size_t ring_byte_length,
    uint32_t read_pointer_dwords,
    uint32_t write_pointer_dwords,
    GuestRingBatch* output,
    std::string* error) {
    constexpr size_t kDwordBytes = sizeof(uint32_t);
    constexpr size_t kMaximumRingBytes = 64u * 1024u * 1024u;
    if (!ring_bytes || !output || ring_byte_length < 8u ||
        ring_byte_length > kMaximumRingBytes ||
        (ring_byte_length & (ring_byte_length - 1u)) != 0u ||
        (ring_byte_length % kDwordBytes) != 0u ||
        ring_byte_length / kDwordBytes > std::numeric_limits<uint32_t>::max()) {
        return fail("invalid Xbox guest ring storage", error);
    }

    const uint32_t ring_dwords =
        static_cast<uint32_t>(ring_byte_length / kDwordBytes);
    if (read_pointer_dwords >= ring_dwords ||
        write_pointer_dwords >= ring_dwords) {
        return fail("Xbox guest ring pointer is outside the ring", error);
    }

    const uint32_t unread_dwords = write_pointer_dwords >= read_pointer_dwords
        ? write_pointer_dwords - read_pointer_dwords
        : ring_dwords - read_pointer_dwords + write_pointer_dwords;
    GuestRingBatch batch{};
    batch.next_read_pointer_dwords = read_pointer_dwords;
    if (unread_dwords == 0u) {
        *output = std::move(batch);
        if (error) error->clear();
        return true;
    }

    const size_t unread_bytes = static_cast<size_t>(unread_dwords) * kDwordBytes;
    const size_t read_offset =
        static_cast<size_t>(read_pointer_dwords) * kDwordBytes;
    const size_t first_bytes =
        std::min(unread_bytes, ring_byte_length - read_offset);
    batch.bytes.resize(unread_bytes);
    std::memcpy(batch.bytes.data(), ring_bytes + read_offset, first_bytes);
    if (first_bytes != unread_bytes) {
        std::memcpy(batch.bytes.data() + first_bytes, ring_bytes,
                    unread_bytes - first_bytes);
    }

    if (!scan_captured_packet_stream(batch.bytes.data(), batch.bytes.size(),
                                     &batch.packets, error)) {
        return false;
    }
    batch.next_read_pointer_dwords = write_pointer_dwords;
    *output = std::move(batch);
    if (error) error->clear();
    return true;
}

}  // namespace shift::xbox
