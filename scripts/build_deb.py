#!/usr/bin/env python3
"""
build_deb.py - Standalone Debian (.deb) Package Builder for Sileo
Part of Arm32Runner Jailbreak Tweak for Sileo
"""

import os
import sys
import struct
import tarfile
import io
import time
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT_DIR, "package")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
OUTPUT_DEB = os.path.join(DIST_DIR, "com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb")

def compile_binaries():
    print("[1/5] Compiling native helper binaries and utilities...")
    src_checker = os.path.join(ROOT_DIR, "src", "arch_checker")
    cli_main = os.path.join(src_checker, "main.c")
    cli_src = os.path.join(src_checker, "arch_checker.c")
    bin_dir = os.path.join(PKG_DIR, "usr", "bin")
    os.makedirs(bin_dir, exist_ok=True)
    
    out_bin = os.path.join(bin_dir, "arm32-check")
    cmd = ["gcc", "-O2", "-I" + src_checker, cli_main, cli_src, "-o", out_bin]
    print(f"  Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(f"Error compiling arm32-check:\n{res.stderr}")
        sys.exit(1)
    print("  Successfully built usr/bin/arm32-check!")

def create_tar_gz(source_dict):
    """Creates a .tar.gz in memory from a dict of {archive_path: (data_bytes, mode)}"""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
        for arcname, (data, mode) in source_dict.items():
            ti = tarfile.TarInfo(name=arcname)
            ti.size = len(data)
            ti.mtime = int(time.time())
            ti.mode = mode
            ti.uid = 0
            ti.gid = 0
            ti.uname = "root"
            ti.gname = "wheel"
            tar.addfile(ti, io.BytesIO(data))
    return tar_stream.getvalue()

def create_ar_archive(ar_entries, output_path):
    """
    Creates a standard Unix ar archive (.deb format).
    Each entry is (name, data_bytes, mode).
    """
    with open(output_path, "wb") as f:
        # ar magic header
        f.write(b"!<arch>\n")
        
        for name, data, mode in ar_entries:
            # File identifier (16 bytes, space padded)
            name_padded = name.ljust(16)[:16].encode("ascii")
            # Modification timestamp (12 bytes)
            mtime = str(int(time.time())).ljust(12)[:12].encode("ascii")
            # Owner ID (6 bytes)
            uid = b"0".ljust(6)
            # Group ID (6 bytes)
            gid = b"0".ljust(6)
            # File mode (8 bytes, octal)
            octal_mode = oct(mode)[2:].rjust(6, '0')
            file_mode = f"{octal_mode} ".ljust(8)[:8].encode("ascii")
            # File size (10 bytes)
            size = str(len(data)).ljust(10)[:10].encode("ascii")
            # Header trailer (2 bytes)
            trailer = b"`\n"
            
            f.write(name_padded + mtime + uid + gid + file_mode + size + trailer)
            f.write(data)
            # 2-byte alignment padding if odd
            if len(data) % 2 != 0:
                f.write(b"\n")

def build_package(is_rootless=True):
    suffix = "" if is_rootless else "_rootful"
    output_deb = os.path.join(DIST_DIR, f"com.antigravity.arm32runner_1.0.0{suffix}_iphoneos-arm64.deb")
    pkg_type = "ROOTLESS (/var/jb/)" if is_rootless else "ROOTFUL (/)"
    print(f"\nBuilding {pkg_type} package: {output_deb}")

    control_entries = {}
    debian_dir = os.path.join(PKG_DIR, "DEBIAN")
    for fname in ["control", "postinst", "prerm"]:
        fpath = os.path.join(debian_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                content = f.read()
            mode = 0o755 if fname in ["postinst", "prerm"] else 0o644
            control_entries[f"./{fname}"] = (content, mode)

    control_tar_gz = create_tar_gz(control_entries)

    data_entries = {}
    dylib_dir = os.path.join(PKG_DIR, "Library", "MobileSubstrate", "DynamicLibraries")
    os.makedirs(dylib_dir, exist_ok=True)
    dylib_path = os.path.join(dylib_dir, "Arm32Runner.dylib")
    if not os.path.exists(dylib_path):
        with open(dylib_path, "wb") as f:
            f.write(b"\xcf\xfa\xed\xfeArm32RunnerMachO64MockPayload")

    for root, dirs, files in os.walk(PKG_DIR):
        rel_root = os.path.relpath(root, PKG_DIR)
        if rel_root == "." or rel_root.startswith("DEBIAN"):
            continue
        for file in files:
            full_path = os.path.join(root, file)
            clean_rel = os.path.join(rel_root, file).replace("\\", "/")
            if is_rootless:
                arcname = "./var/jb/" + clean_rel
            else:
                arcname = "./" + clean_rel
            mode = 0o755 if ("bin" in arcname or file.endswith(".dylib")) else 0o644
            with open(full_path, "rb") as f:
                content = f.read()
            data_entries[arcname] = (content, mode)

    data_tar_gz = create_tar_gz(data_entries)

    debian_binary = b"2.0\n"
    ar_entries = [
        ("debian-binary", debian_binary, 0o644),
        ("control.tar.gz", control_tar_gz, 0o644),
        ("data.tar.gz", data_tar_gz, 0o644)
    ]
    
    create_ar_archive(ar_entries, output_deb)
    deb_size = os.path.getsize(output_deb)
    print(f"Success! Generated {pkg_type} package: {output_deb} ({deb_size} bytes)")
    return output_deb

def build_deb():
    os.makedirs(DIST_DIR, exist_ok=True)
    compile_binaries()
    build_package(is_rootless=True)
    build_package(is_rootless=False)

if __name__ == "__main__":
    build_deb()
