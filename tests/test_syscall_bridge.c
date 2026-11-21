/**
 * test_syscall_bridge.c - Verification Suite for Darwin Syscall Bridge
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../src/syscall_bridge/syscall_bridge.h"

static void test_getpid_syscall(void) {
    SyscallBridgeContext ctx;
    uint8_t dummy_mem[4096];
    bool ok = syscall_bridge_init(&ctx, dummy_mem, sizeof(dummy_mem));
    assert(ok);

    Arm32Regs regs;
    memset(&regs, 0, sizeof(regs));
    regs.r7 = DARWIN_SYS_getpid;

    int32_t ret = syscall_bridge_dispatch(&ctx, &regs);
    printf("[TEST PASS] SYS_getpid dispatched. Returned PID: %d (r0=%u)\n", ret, regs.r0);
    assert(ret > 0);
    assert(regs.r0 == (uint32_t)ret);
    assert(ctx.translated_syscalls == 1);
}

static void test_getuid_syscall(void) {
    SyscallBridgeContext ctx;
    uint8_t dummy_mem[4096];
    syscall_bridge_init(&ctx, dummy_mem, sizeof(dummy_mem));

    Arm32Regs regs;
    memset(&regs, 0, sizeof(regs));
    regs.r7 = DARWIN_SYS_getuid;

    int32_t ret = syscall_bridge_dispatch(&ctx, &regs);
    printf("[TEST PASS] SYS_getuid dispatched. Returned mobile UID: %d (r0=%u)\n", ret, regs.r0);
    assert(ret == 501);
    assert(regs.r0 == 501);
}

static void test_guest_to_host_bounds(void) {
    SyscallBridgeContext ctx;
    uint8_t dummy_mem[1024];
    syscall_bridge_init(&ctx, dummy_mem, sizeof(dummy_mem));

    void *ptr1 = syscall_bridge_guest_to_host(&ctx, 100);
    assert(ptr1 == (void *)(dummy_mem + 100));

    void *ptr_oob = syscall_bridge_guest_to_host(&ctx, 2048);
    assert(ptr_oob == NULL);
    printf("[TEST PASS] Memory boundary check verified (OOB returned NULL)\n");
}

#if defined(_WIN32)
#include <sys/stat.h>
#include <sys/types.h>
#endif

static void test_stat_translation(void) {
    darwin_stat32_t s32;
    memset(&s32, 0, sizeof(s32));

#if defined(_WIN32)
    struct _stat64i32 host_st;
    memset(&host_st, 0, sizeof(host_st));
    host_st.st_dev = 12;
    host_st.st_ino = 54321;
    host_st.st_mode = 0100644;
    host_st.st_size = 987654;
    host_st.st_atime = 1700000000;
    host_st.st_mtime = 1700000500;

    syscall_bridge_translate_stat(&host_st, &s32);

    assert(s32.st_dev == 12);
    assert(s32.st_ino == 54321);
    assert(s32.st_mode == 0100644);
    assert(s32.st_size == 987654);
    assert(s32.st_atimespec.tv_sec == 1700000000);
    assert(s32.st_mtimespec.tv_sec == 1700000500);
    assert(s32.st_blksize == 4096);
#else
    struct stat host_st;
    memset(&host_st, 0, sizeof(host_st));
    host_st.st_dev = 12;
    host_st.st_ino = 123456789;
    host_st.st_mode = 0100644;
    host_st.st_size = 987654;
    host_st.st_atime = 1700000000;
    host_st.st_mtime = 1700000500;

    syscall_bridge_translate_stat(&host_st, &s32);

    assert(s32.st_dev == 12);
    assert(s32.st_ino == 123456789);
    assert(s32.st_mode == 0100644);
    assert(s32.st_size == 987654);
    assert(s32.st_atimespec.tv_sec == 1700000000);
    assert(s32.st_mtimespec.tv_sec == 1700000500);
    assert(s32.st_blksize == 4096);
#endif
    printf("[TEST PASS] Stat translation (host stat -> darwin_stat32) verified\n");
}

int main(void) {
    printf("Starting Arm32Runner Syscall Bridge Test Suite...\n");
    test_getpid_syscall();
    test_getuid_syscall();
    test_guest_to_host_bounds();
    test_stat_translation();
    printf("ALL SYSCALL BRIDGE TESTS PASSED SUCCESSFULLY!\n");
    return 0;
}
