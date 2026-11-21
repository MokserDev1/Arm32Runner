/**
 * syscall_bridge.c - Syscall Translation Bridge Implementation
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include "syscall_bridge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#if defined(_WIN32)
#include <io.h>
#include <process.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#else
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/mman.h>
#endif

bool syscall_bridge_init(SyscallBridgeContext *ctx, uint8_t *guest_memory, size_t memory_size) {
    if (!ctx) return false;
    ctx->guest_base = guest_memory;
    ctx->guest_size = memory_size;
    ctx->is_rootless = false;
    ctx->total_syscalls = 0;
    ctx->translated_syscalls = 0;
    ctx->failed_syscalls = 0;
    return true;
}

void *syscall_bridge_guest_to_host(SyscallBridgeContext *ctx, uint32_t guest_addr) {
    if (!ctx || !ctx->guest_base) {
        /* Direct address mapping if 1:1 mapping in 4GB segment */
        return (void *)(uintptr_t)guest_addr;
    }
    if (guest_addr >= ctx->guest_size) {
        return NULL;
    }
    return (void *)(ctx->guest_base + guest_addr);
}

void syscall_bridge_translate_stat(const void *host_stat_buf, darwin_stat32_t *out_stat32) {
    if (!host_stat_buf || !out_stat32) return;
    memset(out_stat32, 0, sizeof(darwin_stat32_t));

#if defined(_WIN32)
    const struct _stat64i32 *st = (const struct _stat64i32 *)host_stat_buf;
    out_stat32->st_dev = (uint32_t)st->st_dev;
    out_stat32->st_ino = (uint64_t)st->st_ino;
    out_stat32->st_mode = (uint16_t)st->st_mode;
    out_stat32->st_nlink = (uint16_t)st->st_nlink;
    out_stat32->st_uid = (uint32_t)st->st_uid;
    out_stat32->st_gid = (uint32_t)st->st_gid;
    out_stat32->st_rdev = (uint32_t)st->st_rdev;
    out_stat32->st_size = (int64_t)st->st_size;
    out_stat32->st_atimespec.tv_sec = (int32_t)st->st_atime;
    out_stat32->st_mtimespec.tv_sec = (int32_t)st->st_mtime;
    out_stat32->st_ctimespec.tv_sec = (int32_t)st->st_ctime;
#else
    const struct stat *st = (const struct stat *)host_stat_buf;
    out_stat32->st_dev = (uint32_t)st->st_dev;
    out_stat32->st_ino = (uint64_t)st->st_ino;
    out_stat32->st_mode = (uint16_t)st->st_mode;
    out_stat32->st_nlink = (uint16_t)st->st_nlink;
    out_stat32->st_uid = (uint32_t)st->st_uid;
    out_stat32->st_gid = (uint32_t)st->st_gid;
    out_stat32->st_rdev = (uint32_t)st->st_rdev;
    out_stat32->st_size = (int64_t)st->st_size;
    out_stat32->st_atimespec.tv_sec = (int32_t)st->st_atime;
    out_stat32->st_mtimespec.tv_sec = (int32_t)st->st_mtime;
    out_stat32->st_ctimespec.tv_sec = (int32_t)st->st_ctime;
#endif
    out_stat32->st_blksize = 4096;
    out_stat32->st_blocks = (out_stat32->st_size + 511) / 512;
}

int32_t syscall_bridge_dispatch(SyscallBridgeContext *ctx, Arm32Regs *regs) {
    if (!regs) return -1;
    if (ctx) ctx->total_syscalls++;

    uint32_t sys_no = regs->r7;
    int32_t ret = 0;

    switch (sys_no) {
        case DARWIN_SYS_exit: {
            uint32_t exit_code = regs->r0;
            if (ctx) ctx->translated_syscalls++;
            /* In real iOS process, exit cleanly */
            exit((int)exit_code);
            break;
        }

        case DARWIN_SYS_getpid: {
#if defined(_WIN32)
            ret = (int32_t)_getpid();
#else
            ret = (int32_t)getpid();
#endif
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_getuid:
        case DARWIN_SYS_geteuid: {
            /* On iOS mobile apps run under mobile user (UID 501) */
            ret = 501;
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_write: {
            int fd = (int)regs->r0;
            uint32_t guest_buf_ptr = regs->r1;
            uint32_t count = regs->r2;
            void *host_buf = syscall_bridge_guest_to_host(ctx, guest_buf_ptr);

            if (!host_buf && count > 0) {
                regs->r0 = (uint32_t)-1;
                if (ctx) ctx->failed_syscalls++;
                return -1;
            }

#if defined(_WIN32)
            ret = (int32_t)_write(fd, host_buf, (unsigned int)count);
#else
            ret = (int32_t)write(fd, host_buf, (size_t)count);
#endif
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_read: {
            int fd = (int)regs->r0;
            uint32_t guest_buf_ptr = regs->r1;
            uint32_t count = regs->r2;
            void *host_buf = syscall_bridge_guest_to_host(ctx, guest_buf_ptr);

            if (!host_buf && count > 0) {
                regs->r0 = (uint32_t)-1;
                if (ctx) ctx->failed_syscalls++;
                return -1;
            }

#if defined(_WIN32)
            ret = (int32_t)_read(fd, host_buf, (unsigned int)count);
#else
            ret = (int32_t)read(fd, host_buf, (size_t)count);
#endif
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_close: {
            int fd = (int)regs->r0;
#if defined(_WIN32)
            ret = _close(fd);
#else
            ret = close(fd);
#endif
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_open: {
            uint32_t path_ptr = regs->r0;
            int flags = (int)regs->r1;
            int mode = (int)regs->r2;
            const char *path = (const char *)syscall_bridge_guest_to_host(ctx, path_ptr);

            if (!path) {
                regs->r0 = (uint32_t)-1;
                if (ctx) ctx->failed_syscalls++;
                return -1;
            }

#if defined(_WIN32)
            int win_flags = _O_RDONLY;
            if (flags & 0x01) win_flags = _O_WRONLY;
            if (flags & 0x02) win_flags = _O_RDWR;
            if (flags & 0x0200) win_flags |= _O_CREAT;
            ret = _open(path, win_flags, mode);
#else
            ret = open(path, flags, mode);
#endif
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_stat:
        case DARWIN_SYS_lstat: {
            uint32_t path_ptr = regs->r0;
            uint32_t stat32_ptr = regs->r1;
            const char *path = (const char *)syscall_bridge_guest_to_host(ctx, path_ptr);
            darwin_stat32_t *out_s = (darwin_stat32_t *)syscall_bridge_guest_to_host(ctx, stat32_ptr);

            if (!path || !out_s) {
                regs->r0 = (uint32_t)-1;
                if (ctx) ctx->failed_syscalls++;
                return -1;
            }

#if defined(_WIN32)
            struct _stat64i32 host_st;
            ret = _stat(path, &host_st);
            if (ret == 0) {
                syscall_bridge_translate_stat(&host_st, out_s);
            }
#else
            struct stat host_st;
            ret = (sys_no == DARWIN_SYS_lstat) ? lstat(path, &host_st) : stat(path, &host_st);
            if (ret == 0) {
                syscall_bridge_translate_stat(&host_st, out_s);
            }
#endif
            regs->r0 = (uint32_t)ret;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        case DARWIN_SYS_gettimeofday: {
            uint32_t tv32_ptr = regs->r0;
            timeval32_t *out_tv = (timeval32_t *)syscall_bridge_guest_to_host(ctx, tv32_ptr);
            if (out_tv) {
#if defined(_WIN32)
                /* Windows fallback */
                out_tv->tv_sec = 1600000000;
                out_tv->tv_usec = 0;
#else
                struct timeval host_tv;
                gettimeofday(&host_tv, NULL);
                out_tv->tv_sec = (int32_t)host_tv.tv_sec;
                out_tv->tv_usec = (int32_t)host_tv.tv_usec;
#endif
            }
            regs->r0 = 0;
            if (ctx) ctx->translated_syscalls++;
            break;
        }

        default:
            /* Unsupported or complex syscall pass-through */
            if (ctx) ctx->failed_syscalls++;
            regs->r0 = (uint32_t)-ENOSYS;
            return -1;
    }

    return ret;
}
