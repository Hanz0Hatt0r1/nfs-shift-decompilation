#ifndef SHIFT_RECOMPILED_PCODE_ABI_H
#define SHIFT_RECOMPILED_PCODE_ABI_H

#include <stddef.h>
#include <stdint.h>

typedef int (*RviReadBytes)(void *, const char *, uint64_t, size_t, uint8_t *);
typedef int (*RviWriteBytes)(void *, const char *, uint64_t, size_t,
                             const uint8_t *);
typedef int (*RviFillMemory)(void *, const char *, uint64_t, uint8_t, size_t);
typedef int (*RviCallFunction)(void *, uint64_t);
typedef int (*RviUseropFunction)(void *, uint32_t, const uint64_t *,
                                 const unsigned *, size_t, uint64_t *,
                                 unsigned);

typedef struct {
    void *opaque;
    RviReadBytes read;
    RviWriteBytes write;
    RviCallFunction call;
    RviUseropFunction userop;
    RviFillMemory fill;
} RviPcodeContext;

#endif
