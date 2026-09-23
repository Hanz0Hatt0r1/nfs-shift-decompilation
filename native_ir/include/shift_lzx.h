#pragma once
#include <cstddef>
#include <cstdint>

extern "C" {
// Returns 0 on success, non-zero on decode/format error.
int shift_xmem_decompress(const std::uint8_t* src, std::size_t src_size,
                          std::uint8_t* dst, std::size_t dst_capacity,
                          std::size_t expected_size);
}
