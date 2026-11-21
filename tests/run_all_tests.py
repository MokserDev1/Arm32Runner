#!/usr/bin/env python3
"""
run_all_tests.py - Complete Test Suite Runner and Package Validator
Part of Arm32Runner Jailbreak Tweak for Sileo
"""

import os
import sys
import subprocess
import tarfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_c_syscall_bridge():
    print("--- [1/3] Building and running C Syscall Bridge Tests ---")
    test_src = os.path.join(ROOT_DIR, "tests", "test_syscall_bridge.c")
    bridge_src = os.path.join(ROOT_DIR, "src", "syscall_bridge", "syscall_bridge.c")
    include_bridge = os.path.join(ROOT_DIR, "src", "syscall_bridge")
    exe_path = os.path.join(ROOT_DIR, "tests", "test_syscall_bridge_runner.exe")
    
    cmd = ["gcc", "-O2", "-I" + include_bridge, test_src, bridge_src, "-o", exe_path]
    res = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(f"Compilation error:\n{res.stderr}")
        return False
        
    run_res = subprocess.run([exe_path], capture_output=True, encoding="utf-8", errors="replace")
    print(run_res.stdout)
    if run_res.returncode != 0:
        print(f"Test failure:\n{run_res.stderr}")
        return False
        
    if os.path.exists(exe_path):
        os.remove(exe_path)
    return True

def test_deb_package_structure():
    print("\n--- [2/3] Building and Validating Debian (.deb) Package for Sileo ---")
    builder_script = os.path.join(ROOT_DIR, "scripts", "build_deb.py")
    res = subprocess.run([sys.executable, builder_script], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"Deb builder failed:\n{res.stderr}")
        return False

    deb_path = os.path.join(ROOT_DIR, "dist", "com.antigravity.arm32runner_1.0.0_iphoneos-arm64.deb")
    if not os.path.exists(deb_path):
        print("Deb file does not exist!")
        return False

    # Validate AR structure
    with open(deb_path, "rb") as f:
        magic = f.read(8)
        assert magic == b"!<arch>\n", f"Invalid AR magic: {magic}"
        
        # Read debian-binary header
        header1 = f.read(60)
        assert b"debian-binary" in header1
        content1 = f.read(4) # 2.0\n
        assert content1 == b"2.0\n"
        
        # Read control.tar.gz header
        header2 = f.read(60)
        assert b"control.tar.gz" in header2
        size2 = int(header2[48:58].strip())
        gz_control = f.read(size2)
        if size2 % 2 != 0: f.read(1) # padding
        
        # Read data.tar.gz header
        header3 = f.read(60)
        assert b"data.tar.gz" in header3
        size3 = int(header3[48:58].strip())
        gz_data = f.read(size3)

    print("  [PASS] Valid Debian Unix AR archive format confirmed")
    print(f"  [PASS] control.tar.gz extracted ({len(gz_control)} bytes)")
    print(f"  [PASS] data.tar.gz extracted ({len(gz_data)} bytes)")
    return True

def test_macho_architecture():
    print("\n--- [3/3] Running Mach-O Architecture Parser Tests ---")
    parser_script = os.path.join(ROOT_DIR, "tests", "test_macho_parser.py")
    res = subprocess.run([sys.executable, parser_script], capture_output=True, text=True)
    print(res.stdout)
    return res.returncode == 0

def main():
    print("=======================================================")
    print("       Arm32Runner Tweak Automated Test Suite          ")
    print("=======================================================\n")
    
    ok1 = test_c_syscall_bridge()
    ok2 = test_deb_package_structure()
    ok3 = test_macho_architecture()

    if ok1 and ok2 and ok3:
        print("\n=======================================================")
        print("  ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY! (3/3) ")
        print("=======================================================")
        sys.exit(0)
    else:
        print("\n[FAIL] One or more tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
