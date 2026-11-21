/**
 * arm32_core.c - ARMv7 Execution Engine Implementation
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include "arm32_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

bool arm32_cpu_init(Arm32Cpu *cpu, LoadedAppImage *image, SyscallBridgeContext *bridge) {
    if (!cpu || !image || !bridge) return false;
    memset(cpu, 0, sizeof(Arm32Cpu));

    cpu->image = image;
    cpu->bridge = bridge;
    cpu->regs.pc = image->entry_point;
    cpu->regs.sp = image->stack_base + image->stack_size - 4096;
    cpu->regs.cpsr = 0x10; // User mode (EL0)
    cpu->is_running = true;
    cpu->thumb_mode = (image->entry_point & 1) != 0;
    if (cpu->thumb_mode) {
        cpu->regs.pc &= ~1;
    }

    return true;
}

static inline uint32_t read_u32(const Arm32Cpu *cpu, uint32_t addr) {
    uint32_t off = addr & (cpu->image->memory_size - 1);
    if (off + 4 <= cpu->image->memory_size) {
        return *(const uint32_t *)(cpu->image->virtual_memory + off);
    }
    return 0;
}

static inline void write_u32(Arm32Cpu *cpu, uint32_t addr, uint32_t val) {
    uint32_t off = addr & (cpu->image->memory_size - 1);
    if (off + 4 <= cpu->image->memory_size) {
        *(uint32_t *)(cpu->image->virtual_memory + off) = val;
    }
}

bool arm32_cpu_step(Arm32Cpu *cpu) {
    if (!cpu || !cpu->is_running) return false;

    uint32_t pc = cpu->regs.pc;
    uint32_t instr = read_u32(cpu, pc);
    cpu->instruction_count++;

    /* Check for ARM SVC instruction: 0x0F000000 mask with 0xEF000000 */
    if ((instr & 0x0F000000) == 0x0F000000) {
        /* SVC Call: invoke syscall bridge */
        syscall_bridge_dispatch(cpu->bridge, &cpu->regs);
        cpu->regs.pc += 4;
        return true;
    }

    /* Basic branch (B / BL) opcode handling */
    if ((instr & 0x0E000000) == 0x0A000000) {
        bool link = (instr & 0x01000000) != 0;
        int32_t offset = (int32_t)((instr & 0x00FFFFFF) << 2);
        if (offset & 0x02000000) {
            offset |= 0xFC000000; // Sign extend
        }
        if (link) {
            cpu->regs.lr = pc + 4;
        }
        cpu->regs.pc = (uint32_t)((int32_t)pc + 8 + offset);
        return true;
    }

    /* BX LR (Return) */
    if ((instr & 0x0FFFFFF0) == 0x012FFF10) {
        uint32_t rm = instr & 0x0F;
        uint32_t target = (rm == 14) ? cpu->regs.lr : cpu->regs.r0;
        if (target == 0) {
            cpu->is_running = false;
            snprintf(cpu->stop_reason, sizeof(cpu->stop_reason), "Return to address 0x0 (exit)");
            return false;
        }
        cpu->regs.pc = target;
        return true;
    }

    /* Default advance PC */
    cpu->regs.pc += 4;
    return true;
}

int arm32_cpu_run(Arm32Cpu *cpu, uint64_t max_instructions) {
    if (!cpu) return -1;

    uint64_t executed = 0;
    while (cpu->is_running) {
        if (!arm32_cpu_step(cpu)) {
            break;
        }
        executed++;
        if (max_instructions > 0 && executed >= max_instructions) {
            snprintf(cpu->stop_reason, sizeof(cpu->stop_reason), "Hit max instruction threshold: %llu", (unsigned long long)max_instructions);
            break;
        }
    }

    return (int)executed;
}
