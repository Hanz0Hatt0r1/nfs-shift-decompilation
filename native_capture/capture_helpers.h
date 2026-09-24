#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>
#include <d3d9.h>

inline std::vector<unsigned char> copy_declaration(const D3DVERTEXELEMENT9* declaration) {
    std::vector<unsigned char> bytes;
    if (!declaration) return bytes;
    constexpr std::size_t MAX_ELEMENTS = 64;
    for (std::size_t i = 0; i < MAX_ELEMENTS; ++i) {
        const auto* element = declaration + i;
        const auto* raw = reinterpret_cast<const unsigned char*>(element);
        bytes.insert(bytes.end(), raw, raw + sizeof(D3DVERTEXELEMENT9));
        if (element->Stream == 0xFF) return bytes;
    }
    return {};
}

inline std::vector<unsigned char> copy_shader(const DWORD* shader) {
    std::vector<unsigned char> bytes;
    if (!shader) return bytes;
    constexpr std::size_t MAX_DWORDS = 1u << 20;
    constexpr DWORD SHADER_END = 0x0000FFFFu;
    for (std::size_t i = 0; i < MAX_DWORDS; ++i) {
        const DWORD value = shader[i];
        const auto* raw = reinterpret_cast<const unsigned char*>(&value);
        bytes.insert(bytes.end(), raw, raw + sizeof(DWORD));
        if (value == SHADER_END) return bytes;
    }
    return {};
}
