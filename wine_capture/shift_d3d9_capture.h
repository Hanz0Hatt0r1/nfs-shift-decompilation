#ifndef SHIFT_D3D9_CAPTURE_H
#define SHIFT_D3D9_CAPTURE_H

#include "windef.h"
#include "d3d9.h"

#ifdef __cplusplus
extern "C" {
#endif

void shift_capture_create_vertex_declaration(
        const void *device, const D3DVERTEXELEMENT9 *elements,
        const void *declaration);

void shift_capture_set_vertex_declaration(
        const void *device, const void *declaration);

void shift_capture_set_stream_source(
        const void *device, UINT stream, const void *vertex_buffer,
        UINT offset_in_bytes, UINT stride);

void shift_capture_set_indices(
        const void *device, const void *index_buffer, D3DFORMAT format);

void shift_capture_set_texture(
        const void *device, UINT stage, const void *texture);

void shift_capture_create_vertex_shader(
        const void *device, const DWORD *byte_code, const void *shader);

void shift_capture_set_vertex_shader(
        const void *device, const void *shader);

void shift_capture_set_vertex_shader_constant_f(
        const void *device, UINT start_register, const float *values,
        UINT vector4f_count);

void shift_capture_create_pixel_shader(
        const void *device, const DWORD *byte_code, const void *shader);

void shift_capture_set_pixel_shader(
        const void *device, const void *shader);

void shift_capture_set_pixel_shader_constant_f(
        const void *device, UINT start_register, const float *values,
        UINT vector4f_count);

void shift_capture_draw_indexed_primitive(
        const void *device, D3DPRIMITIVETYPE primitive_type,
        INT base_vertex_index, UINT min_vertex_index, UINT vertex_count,
        UINT start_index, UINT primitive_count);

void shift_capture_present(const void *device);

#ifdef __cplusplus
}
#endif

#endif /* SHIFT_D3D9_CAPTURE_H */
