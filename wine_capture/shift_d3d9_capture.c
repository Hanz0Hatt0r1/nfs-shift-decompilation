/*
 * Native Wine D3D9 runtime evidence producer for the Need for Speed: SHIFT
 * decompilation project.
 *
 * This file is intended to be copied into Wine's dlls/d3d9 directory by
 * tools/inject_wine_d3d9_capture.py.
 *
 * The producer is deliberately small and C-only so it can be built as part of
 * Wine's existing 32-bit d3d9.dll. It writes the same event names and JSONL
 * fields consumed by d3d9_capture_schema.py / d3d9_runtime_trace.py.
 */

#include "shift_d3d9_capture.h"

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#define SHIFT_CAPTURE_MAX_DECL_ELEMENTS 256
#define SHIFT_CAPTURE_MAX_SHADER_DWORDS (64u * 1024u)

static INIT_ONCE capture_once = INIT_ONCE_STATIC_INIT;
static CRITICAL_SECTION capture_cs;
static BOOL capture_enabled;
static FILE *capture_file;
static unsigned long long capture_event_index;
static unsigned long long capture_frame;

static BOOL CALLBACK shift_capture_init_once(INIT_ONCE *once, void *parameter, void **context)
{
    const char *path;

    InitializeCriticalSection(&capture_cs);

    path = getenv("SHIFT_D3D9_CAPTURE");
    if (!path || !*path)
        return TRUE;

    capture_file = fopen(path, "ab");
    if (!capture_file)
        return TRUE;

    capture_enabled = TRUE;
    return TRUE;
}

static BOOL shift_capture_init(void)
{
    return InitOnceExecuteOnce(&capture_once, shift_capture_init_once, NULL, NULL)
            && capture_enabled;
}

static void write_ptr(FILE *file, const char *key, const void *value, BOOL comma)
{
    if (comma) fputc(',', file);

    fprintf(file, "\"%s\":", key);
    if (!value)
        fputs("null", file);
    else
        fprintf(file, "\"0x%lx\"", (unsigned long)(uintptr_t)value);
}

static FILE *begin_event(const char *event, const void *device)
{
    if (!shift_capture_init())
        return NULL;

    EnterCriticalSection(&capture_cs);

    fprintf(capture_file,
            "{\"event_index\":%llu,\"frame\":%llu,\"thread_id\":%lu,"
            "\"event\":\"%s\",\"device_ptr\":",
            capture_event_index, capture_frame,
            (unsigned long)GetCurrentThreadId(), event);

    if (!device)
        fputs("null", capture_file);
    else
        fprintf(capture_file, "\"0x%lx\"", (unsigned long)(uintptr_t)device);

    return capture_file;
}

static void end_event(void)
{
    fputs("}\n", capture_file);
    fflush(capture_file);
    ++capture_event_index;
    LeaveCriticalSection(&capture_cs);
}

static void write_hex(FILE *file, const void *data, size_t size)
{
    static const char digits[] = "0123456789abcdef";
    const unsigned char *bytes = data;
    size_t i;

    for (i = 0; i < size; ++i)
    {
        fputc(digits[bytes[i] >> 4], file);
        fputc(digits[bytes[i] & 0x0f], file);
    }
}

static size_t declaration_size(const D3DVERTEXELEMENT9 *elements)
{
    size_t i;

    if (!elements)
        return 0;

    for (i = 0; i < SHIFT_CAPTURE_MAX_DECL_ELEMENTS; ++i)
    {
        if (elements[i].Stream == 0xff)
            return (i + 1) * sizeof(D3DVERTEXELEMENT9);
    }

    return 0;
}

static size_t shader_size(const DWORD *byte_code)
{
    size_t i;

    if (!byte_code)
        return 0;

    /*
     * D3D9 shader bytecode is a DWORD token stream terminated by END.
     * Comment payloads are skipped so a literal 0xffff inside a comment
     * does not become a false terminator.
     */
    for (i = 0; i < SHIFT_CAPTURE_MAX_SHADER_DWORDS; ++i)
    {
        DWORD token = byte_code[i];
        DWORD opcode = token & 0x0000ffffu;

        if (opcode == 0x0000ffffu)
            return (i + 1) * sizeof(DWORD);

        if (opcode == 0x0000fffeu)
        {
            size_t comment_words = (token >> 16) & 0x7fffu;

            if (comment_words > SHIFT_CAPTURE_MAX_SHADER_DWORDS - i - 1)
                return 0;

            i += comment_words;
        }
    }

    return 0;
}

static void write_float_values(FILE *file, const float *values, size_t count)
{
    size_t i;

    fputc('[', file);
    for (i = 0; i < count; ++i)
    {
        if (i)
            fputc(',', file);

        if (!isfinite(values[i]))
            fputs("null", file);
        else
            fprintf(file, "%.9g", values[i]);
    }
    fputc(']', file);
}

void shift_capture_create_vertex_declaration(
        const void *device, const D3DVERTEXELEMENT9 *elements,
        const void *declaration)
{
    FILE *file;
    size_t size;

    if (!(file = begin_event("create_vertex_declaration", device)))
        return;

    write_ptr(file, "declaration_ptr", declaration, TRUE);
    size = declaration_size(elements);

    fprintf(file, ",\"bytes_hex\":\"");
    if (size)
        write_hex(file, elements, size);
    fputs("\"", file);

    end_event();
}

void shift_capture_set_vertex_declaration(
        const void *device, const void *declaration)
{
    FILE *file;

    if (!(file = begin_event("set_vertex_declaration", device)))
        return;

    write_ptr(file, "declaration_ptr", declaration, TRUE);

    end_event();
}

void shift_capture_set_stream_source(
        const void *device, UINT stream, const void *vertex_buffer,
        UINT offset_in_bytes, UINT stride)
{
    FILE *file;

    if (!(file = begin_event("set_stream_source", device)))
        return;

    fprintf(file, ",\"stream\":%u,\"vertex_buffer_ptr\":", stream);
    if (!vertex_buffer)
        fputs("null", file);
    else
        fprintf(file, "\"0x%lx\"", (unsigned long)(uintptr_t)vertex_buffer);

    fprintf(file, ",\"offset_in_bytes\":%u,\"stride\":%u",
            offset_in_bytes, stride);

    end_event();
}

void shift_capture_set_indices(
        const void *device, const void *index_buffer, D3DFORMAT format)
{
    FILE *file;

    if (!(file = begin_event("set_indices", device)))
        return;

    write_ptr(file, "index_buffer_ptr", index_buffer, TRUE);
    fprintf(file, ",\"format\":%u", (unsigned int)format);

    end_event();
}

void shift_capture_set_texture(
        const void *device, UINT stage, const void *texture)
{
    FILE *file;

    if (!(file = begin_event("set_texture", device)))
        return;

    fprintf(file, ",\"stage\":%u,\"texture_ptr\":", stage);
    if (!texture)
        fputs("null", file);
    else
        fprintf(file, "\"0x%lx\"", (unsigned long)(uintptr_t)texture);

    end_event();
}

static void capture_create_shader(
        const char *event, const void *device, const DWORD *byte_code,
        const void *shader)
{
    FILE *file;
    size_t size;

    if (!(file = begin_event(event, device)))
        return;

    write_ptr(file, "shader_ptr", shader, TRUE);
    size = shader_size(byte_code);

    fprintf(file, ",\"bytes_hex\":\"");
    if (size)
        write_hex(file, byte_code, size);
    fputs("\"", file);

    end_event();
}

void shift_capture_create_vertex_shader(
        const void *device, const DWORD *byte_code, const void *shader)
{
    capture_create_shader("create_vertex_shader", device, byte_code, shader);
}

void shift_capture_set_vertex_shader(
        const void *device, const void *shader)
{
    FILE *file;

    if (!(file = begin_event("set_vertex_shader", device)))
        return;

    write_ptr(file, "shader_ptr", shader, TRUE);

    end_event();
}

void shift_capture_set_vertex_shader_constant_f(
        const void *device, UINT start_register, const float *values,
        UINT vector4f_count)
{
    FILE *file;
    size_t count = (size_t)vector4f_count * 4;

    if (!(file = begin_event("set_vertex_shader_constant_f", device)))
        return;

    fprintf(file, ",\"start_register\":%u,\"vector4f_count\":%u,\"values\":",
            start_register, vector4f_count);
    write_float_values(file, values, count);

    end_event();
}

void shift_capture_create_pixel_shader(
        const void *device, const DWORD *byte_code, const void *shader)
{
    capture_create_shader("create_pixel_shader", device, byte_code, shader);
}

void shift_capture_set_pixel_shader(
        const void *device, const void *shader)
{
    FILE *file;

    if (!(file = begin_event("set_pixel_shader", device)))
        return;

    write_ptr(file, "shader_ptr", shader, TRUE);

    end_event();
}

void shift_capture_set_pixel_shader_constant_f(
        const void *device, UINT start_register, const float *values,
        UINT vector4f_count)
{
    FILE *file;
    size_t count = (size_t)vector4f_count * 4;

    if (!(file = begin_event("set_pixel_shader_constant_f", device)))
        return;

    fprintf(file, ",\"start_register\":%u,\"vector4f_count\":%u,\"values\":",
            start_register, vector4f_count);
    write_float_values(file, values, count);

    end_event();
}

void shift_capture_draw_indexed_primitive(
        const void *device, D3DPRIMITIVETYPE primitive_type,
        INT base_vertex_index, UINT min_vertex_index, UINT vertex_count,
        UINT start_index, UINT primitive_count)
{
    FILE *file;

    if (!(file = begin_event("draw_indexed_primitive", device)))
        return;

    fprintf(file,
            ",\"primitive_type\":%u,\"base_vertex_index\":%ld,"
            "\"min_vertex_index\":%u,\"vertex_count\":%u,"
            "\"start_index\":%u,\"primitive_count\":%u",
            (unsigned int)primitive_type, (long)base_vertex_index,
            min_vertex_index, vertex_count, start_index, primitive_count);

    end_event();
}

void shift_capture_present(const void *device)
{
    if (!device || !shift_capture_init())
        return;

    EnterCriticalSection(&capture_cs);
    ++capture_frame;
    LeaveCriticalSection(&capture_cs);
}
