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

uint32_t read_guest_dword(const uint8_t* bytes) {
    return (static_cast<uint32_t>(bytes[0]) << 24) |
           (static_cast<uint32_t>(bytes[1]) << 16) |
           (static_cast<uint32_t>(bytes[2]) << 8) | bytes[3];
}

class GuestIndirectBufferExpander {
public:
    GuestIndirectBufferExpander(
        GuestMemoryReadCallback read_guest_memory,
        void* read_context)
        : read_guest_memory_(read_guest_memory), read_context_(read_context) {}

    bool expand(
        const uint8_t* bytes,
        size_t byte_length,
        ExpandedGuestCommandStream* output,
        std::string* error) {
        if (!output || (byte_length && !bytes)) {
            return fail("invalid Xbox guest command stream", error);
        }
        if (byte_length > kMaximumRootStreamBytes) {
            return fail("Xbox guest ring batch exceeds expansion input limit", error);
        }

        ExpandedGuestCommandStream expanded{};
        if (!append_stream(bytes, byte_length, 0u, 0u, &expanded, error)) {
            return false;
        }
        *output = std::move(expanded);
        if (error) error->clear();
        return true;
    }

private:
    static constexpr uint32_t kIndirectBufferOpcode = 0x3Fu;
    static constexpr uint32_t kMaximumNestingDepth = 8u;
    static constexpr uint32_t kMaximumIndirectBufferCount = 4096u;
    static constexpr size_t kMaximumRootStreamBytes = 64u * 1024u * 1024u;
    static constexpr size_t kMaximumExpandedBytes = 256u * 1024u * 1024u;
    static constexpr size_t kMaximumPacketCount = 1u << 20;

    bool append_stream(
        const uint8_t* bytes,
        size_t byte_length,
        uint32_t source_guest_address,
        uint32_t nesting_depth,
        ExpandedGuestCommandStream* output,
        std::string* error) {
        std::vector<PacketSpan> packet_spans;
        if (!scan_captured_packet_stream(bytes, byte_length, &packet_spans, error)) {
            return false;
        }

        for (const PacketSpan& packet : packet_spans) {
            if (output->packets.size() >= kMaximumPacketCount) {
                return fail("expanded Xbox PM4 packet limit exceeded", error);
            }
            ResolvedGuestPacket resolved{packet, source_guest_address,
                                         byte_length, nesting_depth};
            if (packet.type == PacketType::Type3 && packet.opcode == 0x58u &&
                packet.byte_length == 16u) {
                std::array<uint8_t, 16> packet_snapshot{};
                std::copy_n(bytes + packet.byte_offset, packet_snapshot.size(),
                            packet_snapshot.begin());
                resolved.event_write_snapshot_index =
                    static_cast<uint32_t>(output->event_write_packet_snapshots.size());
                output->event_write_packet_snapshots.push_back(packet_snapshot);
            }
            output->packets.push_back(resolved);

            if (packet.type != PacketType::Type3 ||
                packet.opcode != kIndirectBufferOpcode) {
                continue;
            }
            if (nesting_depth >= kMaximumNestingDepth ||
                output->indirect_buffer_count >= kMaximumIndirectBufferCount) {
                return fail("Xbox PM4 indirect-buffer nesting limit exceeded", error);
            }

            CapturedIndirectBuffer indirect_buffer{};
            if (!decode_captured_indirect_buffer(
                    bytes + packet.byte_offset, packet.byte_length,
                    &indirect_buffer, error)) {
                return false;
            }

            for (const CapturedIndirectBuffer& active : active_buffers_) {
                if (active.guest_address == indirect_buffer.guest_address &&
                    active.dword_count == indirect_buffer.dword_count) {
                    return fail("cyclic Xbox PM4 indirect buffer", error);
                }
            }

            const size_t indirect_byte_length =
                static_cast<size_t>(indirect_buffer.dword_count) * sizeof(uint32_t);
            if (indirect_byte_length >
                kMaximumExpandedBytes - output->indirect_buffer_bytes) {
                return fail("Xbox PM4 indirect-buffer byte limit exceeded", error);
            }
            if (!read_guest_memory_) {
                return fail("Xbox PM4 indirect buffer has no guest-memory reader", error);
            }

            const uint8_t* indirect_bytes = nullptr;
            size_t available_bytes = 0;
            if (!read_guest_memory_(read_context_, indirect_buffer.guest_address,
                                    indirect_byte_length, &indirect_bytes,
                                    &available_bytes) ||
                !indirect_bytes || available_bytes < indirect_byte_length) {
                return fail("Xbox PM4 indirect-buffer span could not be resolved", error);
            }

            output->indirect_buffer_bytes += indirect_byte_length;
            ++output->indirect_buffer_count;
            active_buffers_.push_back(indirect_buffer);
            const bool appended = append_stream(
                indirect_bytes, indirect_byte_length, indirect_buffer.guest_address,
                nesting_depth + 1u, output, error);
            active_buffers_.pop_back();
            if (!appended) return false;
        }
        return true;
    }

    GuestMemoryReadCallback read_guest_memory_;
    void* read_context_;
    std::vector<CapturedIndirectBuffer> active_buffers_;
};

}  // namespace

bool guest_ring_byte_length_from_size_log2(
    uint32_t size_log2,
    size_t* output,
    std::string* error) {
    constexpr uint32_t kMaximumSizeLog2 = 23u;
    if (!output || size_log2 > kMaximumSizeLog2) {
        return fail("invalid Xbox guest ring size_log2", error);
    }
    *output = size_t{1} << (size_log2 + 3u);
    if (error) error->clear();
    return true;
}

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

bool expand_guest_indirect_buffers(
    const GuestRingBatch& root_batch,
    GuestMemoryReadCallback read_guest_memory,
    void* read_context,
    ExpandedGuestCommandStream* output,
    std::string* error) {
    GuestIndirectBufferExpander expander(read_guest_memory, read_context);
    return expander.expand(root_batch.bytes.data(), root_batch.bytes.size(), output, error);
}

bool decode_guest_event_write_shd(
    const uint8_t* packet_bytes,
    size_t packet_byte_length,
    DecodedEventWriteShd* output,
    std::string* error) {
    constexpr size_t kPacketBytes = 4u * sizeof(uint32_t);
    if (!packet_bytes || !output || packet_byte_length != kPacketBytes) {
        return fail("invalid EVENT_WRITE_SHD packet length", error);
    }

    const uint32_t header = read_guest_dword(packet_bytes);
    const uint32_t count = ((header >> 16) & 0x3FFFu) + 1u;
    if ((header >> 30) != 3u || ((header >> 8) & 0xFFu) != 0x58u ||
        count != 3u) {
        return fail("unsupported EVENT_WRITE_SHD packet header", error);
    }

    const uint32_t encoded_address = read_guest_dword(packet_bytes + 8u);
    DecodedEventWriteShd decoded{};
    decoded.initiator = read_guest_dword(packet_bytes + 4u);
    decoded.guest_address = encoded_address & ~uint32_t{3};
    decoded.endian_mode = encoded_address & 3u;
    decoded.value = read_guest_dword(packet_bytes + 12u);
    *output = decoded;
    if (error) error->clear();
    return true;
}

uint32_t event_write_shd_value(
    const DecodedEventWriteShd& event,
    uint32_t swap_counter) {
    return event.initiator & 0x80000000u ? swap_counter : event.value;
}

}  // namespace shift::xbox
