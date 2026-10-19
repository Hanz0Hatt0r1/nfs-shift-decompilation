#pragma once
#ifdef __cplusplus
#include <cstddef>
#include <cstdint>
#else
#include <stddef.h>
#include <stdint.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif
// Returns 0 on success, non-zero on decode/format error.
int shift_xmem_decompress(const uint8_t* src, size_t src_size, uint8_t* dst,
                          size_t dst_capacity, size_t expected_size);

int shift_xmem_decompressed_size(const uint8_t* src, size_t src_size,
                                 size_t* decoded_size);

// Decode a complete framed XMem stream and return its decoded byte count.
int shift_xmem_decompress_auto(const uint8_t* src, size_t src_size,
                               uint8_t* dst, size_t dst_capacity,
                               size_t* decoded_size);
#ifdef __cplusplus
}
#endif
