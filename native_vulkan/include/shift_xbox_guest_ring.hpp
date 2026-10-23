#pragma once

#include "shift_xbox_draw_input.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::xbox {

struct GuestRingBatch {
    std::vector<uint8_t> bytes;
    std::vector<PacketSpan> packets;
    uint32_t next_read_pointer_dwords = 0;
};

// ReXGlue's InitializeRingBuffer size_log2 describes 1 << (size_log2 + 3)
// bytes. Reject values outside the same 64 MiB ceiling as the snapshot reader.
bool guest_ring_byte_length_from_size_log2(
    uint32_t size_log2,
    size_t* output,
    std::string* error);

// Copies and frames the committed dword span of an Xbox guest ring. Read and
// write pointers are dword indexes; packet data remains in guest byte order.
// This is input transport only: it does not apply GPU state or issue draws.
bool snapshot_guest_ring_batch(
    const uint8_t* ring_bytes,
    size_t ring_byte_length,
    uint32_t read_pointer_dwords,
    uint32_t write_pointer_dwords,
    GuestRingBatch* output,
    std::string* error);

}  // namespace shift::xbox
