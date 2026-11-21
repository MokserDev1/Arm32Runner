/**
 * macho_loader.c - Mach-O 32-bit Binary In-Memory Loader Implementation
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include "macho_loader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(_WIN32)
#include <sys/mman.h>
#endif

typedef struct {
    uint32_t cmd;
    uint32_t cmdsize;
    char segname[16];
    uint32_t vmaddr;
    uint32_t vmsize;
    uint32_t fileoff;
    uint32_t filesize;
    uint32_t maxprot;
    uint32_t initprot;
    uint32_t nsects;
    uint32_t flags;
} SegmentCommand32;

bool macho_loader_init(LoadedAppImage *image, size_t reserve_size) {
    if (!image) return false;
    memset(image, 0, sizeof(LoadedAppImage));

    if (reserve_size == 0) {
        reserve_size = 128 * 1024 * 1024; // Default 128 MB space
    }

    image->virtual_memory = (uint8_t *)calloc(1, reserve_size);
    if (!image->virtual_memory) {
        snprintf(image->error_desc, sizeof(image->error_desc), "Failed to allocate 32-bit virtual memory");
        return false;
    }

    image->memory_size = reserve_size;
    image->stack_size = 8 * 1024 * 1024; // 8 MB stack
    image->stack_base = (uint32_t)(reserve_size - image->stack_size);
    return true;
}

bool macho_loader_load(LoadedAppImage *image, const char *binary_path, const MachOAnalysisResult *meta) {
    if (!image || !binary_path || !meta || !image->virtual_memory) {
        if (image) snprintf(image->error_desc, sizeof(image->error_desc), "Invalid arguments to macho_loader_load");
        return false;
    }

    FILE *f = fopen(binary_path, "rb");
    if (!f) {
        snprintf(image->error_desc, sizeof(image->error_desc), "Failed to open binary: %s", binary_path);
        return false;
    }

    uint32_t slice_offset = meta->arm32_offset;
    uint32_t slice_size = meta->arm32_size;

    fseek(f, (long)slice_offset, SEEK_SET);
    uint8_t *slice_buf = (uint8_t *)malloc(slice_size);
    if (!slice_buf) {
        fclose(f);
        snprintf(image->error_desc, sizeof(image->error_desc), "Memory allocation for slice failed");
        return false;
    }

    size_t rd = fread(slice_buf, 1, slice_size, f);
    fclose(f);

    if (rd != slice_size) {
        free(slice_buf);
        snprintf(image->error_desc, sizeof(image->error_desc), "Failed to read slice data");
        return false;
    }

    /* Iterate through load commands in slice to map segments */
    const uint8_t *ptr = slice_buf;
    uint32_t ncmds = *(const uint32_t *)(ptr + 16);
    const uint8_t *cmd_ptr = ptr + 28; // sizeof(mach_header)

    for (uint32_t i = 0; i < ncmds; i++) {
        if ((size_t)(cmd_ptr - slice_buf) + 8 > slice_size) break;
        uint32_t cmd = *(const uint32_t *)cmd_ptr;
        uint32_t cmdsize = *(const uint32_t *)(cmd_ptr + 4);

        if (cmd == LC_SEGMENT_32) {
            const SegmentCommand32 *seg = (const SegmentCommand32 *)cmd_ptr;
            if (seg->vmsize > 0 && seg->filesize > 0) {
                if (strncmp(seg->segname, "__PAGEZERO", 10) != 0) {
                    uint32_t dest_off = seg->vmaddr & (image->memory_size - 1);
                    if (dest_off + seg->filesize <= image->memory_size && seg->fileoff + seg->filesize <= slice_size) {
                        memcpy(image->virtual_memory + dest_off, slice_buf + seg->fileoff, seg->filesize);
                        if (strncmp(seg->segname, "__TEXT", 6) == 0) {
                            image->text_vmaddr = seg->vmaddr;
                            image->text_vmsize = seg->vmsize;
                        } else if (strncmp(seg->segname, "__DATA", 6) == 0) {
                            image->data_vmaddr = seg->vmaddr;
                            image->data_vmsize = seg->vmsize;
                        }
                    }
                }
            }
        }
        cmd_ptr += cmdsize;
    }

    image->entry_point = meta->entry_point != 0 ? meta->entry_point : image->text_vmaddr;
    image->is_loaded = true;
    free(slice_buf);
    return true;
}

void macho_loader_destroy(LoadedAppImage *image) {
    if (!image) return;
    if (image->virtual_memory) {
        free(image->virtual_memory);
        image->virtual_memory = NULL;
    }
    image->is_loaded = false;
}
