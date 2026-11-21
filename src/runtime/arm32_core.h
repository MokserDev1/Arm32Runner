/**
 * arm32_core.h - ARMv7 Execution Engine & CPU State
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#ifndef ARM32_CORE_H
#define ARM32_CORE_H

#include <stdint.h>
#include <stdbool.h>
#include "../syscall_bridge/syscall_bridge.h"
#include "macho_loader.h"

typedef struct {
    Arm32Regs regs;
    LoadedAppImage *image;
    SyscallBridgeContext *bridge;
    bool is_running;
    bool thumb_mode;
    uint64_t instruction_count;
    char stop_reason[128];
} Arm32Cpu;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Initializes CPU state, registers, stack pointer, and links syscall bridge.
 */
bool arm32_cpu_init(Arm32Cpu *cpu, LoadedAppImage *image, SyscallBridgeContext *bridge);

/**
 * Runs execution starting from current PC until exit, breakpoint, or max_instructions.
 * If max_instructions == 0, executes indefinitely until termination.
 */
int arm32_cpu_run(Arm32Cpu *cpu, uint64_t max_instructions);

/**
 * Steps one instruction forward.
 */
bool arm32_cpu_step(Arm32Cpu *cpu);

#ifdef __cplusplus
}
#endif

#endif /* ARM32_CORE_H */
