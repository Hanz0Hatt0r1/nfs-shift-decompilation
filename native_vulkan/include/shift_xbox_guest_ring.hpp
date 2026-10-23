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
