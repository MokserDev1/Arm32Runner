/**
 * syscall_bridge.h - Syscall Translation Bridge Interface
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#ifndef SYSCALL_BRIDGE_H
#define SYSCALL_BRIDGE_H

#include "syscall_types.h"
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef struct {
    uint32_t r0;
    uint32_t r1;
    uint32_t r2;
    uint32_t r3;
    uint32_t r4;
    uint32_t r5;
    uint32_t r6;
    uint32_t r7; /* Syscall number in ARM EABI / Darwin */
    uint32_t r8;
    uint32_t r9;
    uint32_t r10;
    uint32_t r11;
    uint32_t r12;
    uint32_t sp;
    uint32_t lr;
    uint32_t pc;
    uint32_t cpsr;
} Arm32Regs;

typedef struct {
    uint8_t *guest_base;     /* Base pointer to 32-bit guest address space */
    size_t guest_size;       /* Typically 2GB - 4GB address reservation */
    bool is_rootless;        /* Running on rootless jailbreak (/var/jb/) */
    uint64_t total_syscalls;
    uint64_t translated_syscalls;
    uint64_t failed_syscalls;
} SyscallBridgeContext;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Initializes the syscall translation bridge with memory context.
 */
bool syscall_bridge_init(SyscallBridgeContext *ctx, uint8_t *guest_memory, size_t memory_size);

/**
 * Translates a 32-bit ARM guest pointer to a 64-bit host pointer.
 * Returns NULL if the guest address is outside valid bounds.
 */
void *syscall_bridge_guest_to_host(SyscallBridgeContext *ctx, uint32_t guest_addr);

/**
 * Handles a Darwin 32-bit syscall invoked via SVC instruction.
 * Translates arguments, executes syscall or shim, and updates r0, r1 and CPSR carry (for error).
 */
int32_t syscall_bridge_dispatch(SyscallBridgeContext *ctx, Arm32Regs *regs);

/**
 * Converts host stat structure to 32-bit Darwin stat32 layout.
 */
void syscall_bridge_translate_stat(const void *host_stat, darwin_stat32_t *out_stat32);

#ifdef __cplusplus
}
#endif

#endif /* SYSCALL_BRIDGE_H */
