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

struct ResolvedGuestPacket {
    PacketSpan packet;
    // Zero for packets copied from the root ring batch. For nested packets,
    // this is the guest address of the indirect buffer containing the packet.
    uint32_t source_guest_address = 0;
    size_t source_guest_buffer_byte_length = 0;
    uint32_t nesting_depth = 0;
};

struct ExpandedGuestCommandStream {
    std::vector<ResolvedGuestPacket> packets;
    size_t indirect_buffer_bytes = 0;
    uint32_t indirect_buffer_count = 0;
};

struct DecodedEventWriteShd {
    uint32_t initiator = 0;
    uint32_t guest_address = 0;
    uint32_t endian_mode = 0;
    uint32_t value = 0;
};

// The returned pointer must remain readable for at least `byte_length` bytes
// until the callback's caller finishes parsing it. `available_bytes` reports
// the readable extent beginning at the returned pointer.
using GuestMemoryReadCallback = bool (*)(
    void* context,
    uint32_t guest_address,
    size_t byte_length,
    const uint8_t** bytes,
    size_t* available_bytes);

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

// Expands only the captured three-dword PM4_INDIRECT_BUFFER form. Other PM4
// packets remain framed but uninterpreted. Expansion is bounded and fails
// without changing output if a span cannot be resolved or parsed.
bool expand_guest_indirect_buffers(
    const GuestRingBatch& root_batch,
    GuestMemoryReadCallback read_guest_memory,
    void* read_context,
    ExpandedGuestCommandStream* output,
    std::string* error);

// EVENT_WRITE_SHD writes a guest-physical dword. The address low two bits
// select Xenos endianness; the returned address is four-byte aligned.
bool decode_guest_event_write_shd(
    const uint8_t* packet_bytes,
    size_t packet_byte_length,
    DecodedEventWriteShd* output,
    std::string* error);
uint32_t event_write_shd_value(
    const DecodedEventWriteShd& event,
    uint32_t swap_counter);

}  // namespace shift::xbox
