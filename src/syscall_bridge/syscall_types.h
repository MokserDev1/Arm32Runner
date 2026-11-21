/**
 * syscall_types.h - 32-bit vs 64-bit ABI Structure Definitions
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#ifndef SYSCALL_TYPES_H
#define SYSCALL_TYPES_H

#include <stdint.h>

#pragma pack(push, 4)

/* 32-bit ARM timeval layout */
typedef struct {
    int32_t tv_sec;
    int32_t tv_usec;
} timeval32_t;

/* 32-bit ARM timespec layout */
typedef struct {
    int32_t tv_sec;
    int32_t tv_nsec;
} timespec32_t;

/* 32-bit ARM stat structure layout (Darwin 32-bit ABI) */
typedef struct {
    uint32_t st_dev;           /* inode's device */
    uint16_t st_mode;          /* inode protection mode */
    uint16_t st_nlink;         /* number of hard links */
    uint64_t st_ino;           /* inode's number */
    uint32_t st_uid;           /* user ID of the owner */
    uint32_t st_gid;           /* group ID of the owner */
    uint32_t st_rdev;          /* device type */
    timespec32_t st_atimespec; /* time of last access */
    timespec32_t st_mtimespec; /* time of last modification */
    timespec32_t st_ctimespec; /* time of last status change */
    timespec32_t st_birthtimespec; /* time of creation */
    int64_t  st_size;          /* file size in bytes */
    int64_t  st_blocks;        /* blocks allocated for file */
    int32_t  st_blksize;       /* optimal blocksize for I/O */
    uint32_t st_flags;         /* user defined flags */
    uint32_t st_gen;           /* file generation number */
    int32_t  st_lspare;        /* RESERVED: DO NOT USE! */
    int64_t  st_qspare[2];     /* RESERVED: DO NOT USE! */
} darwin_stat32_t;

/* 32-bit ARM iovec structure */
typedef struct {
    uint32_t iov_base; /* 32-bit user virtual pointer */
    uint32_t iov_len;  /* length in bytes */
} iovec32_t;

/* 32-bit ARM rlimit structure */
typedef struct {
    uint64_t rlim_cur;
    uint64_t rlim_max;
} rlimit32_t;

#pragma pack(pop)

/* Standard Darwin 32-bit Syscall Numbers */
#define DARWIN_SYS_syscall          0
#define DARWIN_SYS_exit             1
#define DARWIN_SYS_fork             2
#define DARWIN_SYS_read             3
#define DARWIN_SYS_write            4
#define DARWIN_SYS_open             5
#define DARWIN_SYS_close            6
#define DARWIN_SYS_wait4            7
#define DARWIN_SYS_unlink           10
#define DARWIN_SYS_chdir            12
#define DARWIN_SYS_chmod            15
#define DARWIN_SYS_chown            16
#define DARWIN_SYS_getpid           20
#define DARWIN_SYS_getuid           24
#define DARWIN_SYS_geteuid          25
#define DARWIN_SYS_access           33
#define DARWIN_SYS_kill             37
#define DARWIN_SYS_stat             38
#define DARWIN_SYS_lseek            199
#define DARWIN_SYS_mmap             197
#define DARWIN_SYS_munmap           73
#define DARWIN_SYS_mprotect         74
#define DARWIN_SYS_select           93
#define DARWIN_SYS_socket           97
#define DARWIN_SYS_connect          98
#define DARWIN_SYS_bind             104
#define DARWIN_SYS_listen           106
#define DARWIN_SYS_gettimeofday     116
#define DARWIN_SYS_writev           121
#define DARWIN_SYS_fstat            189
#define DARWIN_SYS_lstat            190
#define DARWIN_SYS_sysctl           202
#define DARWIN_SYS_shm_open         266
#define DARWIN_SYS_shm_unlink       267
#define DARWIN_SYS_bsdthread_create 360
#define DARWIN_SYS_bsdthread_terminate 361
#define DARWIN_SYS_stat64           338
#define DARWIN_SYS_fstat64          339
#define DARWIN_SYS_lstat64          340

#endif /* SYSCALL_TYPES_H */
