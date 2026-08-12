# -*- coding: utf-8 -*-
"""Build cef_helper.exe from CEF binary distribution (local + CI).

Prereqs in third_party/:
  w64devkit/                  (MinGW toolchain)
  cef_binary_*/               (CEF windows64 minimal)
  cef.tar.bz2                 (optional - downloaded if missing)
  w64devkit.7z.exe            (optional - downloaded if missing)
"""
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))  # third_party
CEF_VERSION = "3.2704.1414.g185cd6c"
CEF_DIR = os.path.join(BASE, f"cef_binary_{CEF_VERSION}_windows64_minimal")
W64DEVKIT_DIR = os.path.join(BASE, "w64devkit")
HELPER_DIR = os.path.join(BASE, "cef_helper")
CEF_URL = f"https://cef-builds.spotifycdn.com/cef_binary_{CEF_VERSION}_windows64_minimal.tar.bz2"
W64DEVKIT_URL = "https://github.com/skeeto/w64devkit/releases/download/v2.9.1/w64devkit-x64-2.9.1.7z.exe"


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
        print(f"skip download {dest}")
        return
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"  -> {os.path.getsize(dest)} bytes")


def setup_toolchain():
    if not os.path.exists(os.path.join(W64DEVKIT_DIR, "bin", "g++.exe")):
        exe = os.path.join(BASE, "w64devkit.7z.exe")
        download(W64DEVKIT_URL, exe)
        print("extracting w64devkit...")
        subprocess.run([exe, "-y"], cwd=BASE, check=False)
    if not os.path.exists(os.path.join(W64DEVKIT_DIR, "bin", "g++.exe")):
        raise SystemExit("w64devkit extraction failed")


def setup_cef():
    if not os.path.exists(os.path.join(CEF_DIR, "Release", "libcef.dll")):
        tarball = os.path.join(BASE, "cef.tar.bz2")
        download(CEF_URL, tarball)
        print("extracting CEF...")
        with tarfile.open(tarball, "r:bz2") as tf:
            tf.extractall(BASE)
    icu = os.path.join(CEF_DIR, "Resources", "icudtl.dat")
    if not os.path.exists(icu):
        raise SystemExit("icudtl.dat missing in CEF Resources")
    return CEF_DIR


def build_helper(cef_dir):
    os.makedirs(HELPER_DIR, exist_ok=True)
    gxx = os.path.join(W64DEVKIT_DIR, "bin", "g++.exe")
    env = dict(os.environ)
    env["PATH"] = os.path.join(W64DEVKIT_DIR, "bin") + ";" + env.get("PATH", "")

    release = os.path.join(cef_dir, "Release")
    dll_a = os.path.join(release, "libcef.dll.a")
    if not os.path.exists(dll_a):
        gendef = os.path.join(W64DEVKIT_DIR, "bin", "gendef.exe")
        dlltool = os.path.join(W64DEVKIT_DIR, "bin", "dlltool.exe")
        subprocess.run([gendef, "libcef.dll"], cwd=release, check=False)
        subprocess.run([dlltool, "--dllname", "libcef.dll",
                        "--def", os.path.join(release, "libcef.def"),
                        "--output-lib", dll_a], cwd=release, check=False)

    obj_dir = os.path.join(HELPER_DIR, "obj")
    os.makedirs(obj_dir, exist_ok=True)
    common = ["-std=c++17", "-O1", "-fpermissive",
              "-D_WIN32_WINNT=0x0A00", "-DUNICODE", "-D_UNICODE", "-DNOMINMAX",
              "-DUSING_CEF_SHARED", "-include", "cstring",
              f"-I{cef_dir}", f"-I{os.path.join(cef_dir, 'include')}"]

    sources = []
    for root, _, files in os.walk(os.path.join(cef_dir, "libcef_dll")):
        for fn in files:
            if fn.endswith(".cc"):
                sources.append(os.path.join(root, fn))

    def build_one(src):
        rel = os.path.relpath(src, os.path.join(cef_dir, "libcef_dll"))
        obj = os.path.join(obj_dir, rel.replace("\\", "_").replace("/", "_") + ".o")
        if os.path.exists(obj):
            return obj
        r = subprocess.run([gxx, "-c", src, "-o", obj] + common,
                           capture_output=True, env=env)
        if r.returncode != 0:
            err = r.stderr.decode("utf-8", errors="replace")
            raise SystemExit(f"compile failed {src}:\n{err[-1500:]}")
        return obj

    objs = [build_one(s) for s in sources]
    r = subprocess.run([gxx, "-c", os.path.join(HELPER_DIR, "cef_helper.cpp"),
                        "-o", os.path.join(obj_dir, "cef_helper.o")] + common,
                       capture_output=True, env=env)
    if r.returncode != 0:
        raise SystemExit(r.stderr.decode("utf-8", errors="replace")[-1500:])
    objs.append(os.path.join(obj_dir, "cef_helper.o"))

    exe = os.path.join(HELPER_DIR, "cef_helper.exe")
    r = subprocess.run([gxx, "-o", exe] + objs +
                       [f"-L{release}", "-l:libcef.dll.a",
                        "-luser32", "-lgdi32", "-lshell32", "-lcomdlg32", "-lole32"],
                       capture_output=True, env=env)
    if r.returncode != 0:
        raise SystemExit(r.stderr.decode("utf-8", errors="replace")[-1500:])
    print(f"cef_helper.exe built: {os.path.getsize(exe)} bytes")
    return exe


def copy_runtime(cef_dir):
    release = os.path.join(cef_dir, "Release")
    for f in ["libcef.dll", "d3dcompiler_43.dll", "d3dcompiler_47.dll",
              "libEGL.dll", "libGLESv2.dll", "natives_blob.bin",
              "snapshot_blob.bin", "widevinecdmadapter.dll"]:
        src = os.path.join(release, f)
        if os.path.exists(src):
            shutil.copy(src, HELPER_DIR)
    shutil.copy(os.path.join(cef_dir, "Resources", "icudtl.dat"), HELPER_DIR)
    res_dst = os.path.join(HELPER_DIR, "Resources")
    if os.path.exists(res_dst):
        shutil.rmtree(res_dst)
    shutil.copytree(os.path.join(cef_dir, "Resources"), res_dst)
    print("runtime copied")


GCC_ATOMICOPS_HEADER = '// GCC x86 atomic operations implementation for CEF (MinGW build).\n// Uses GCC __sync builtins (portable, correct on x86/x64).\n// The CEF minimal distribution does not ship this header.\n#ifndef CEF_INCLUDE_BASE_INTERNAL_CEF_ATOMICOPS_X86_GCC_H_\n#define CEF_INCLUDE_BASE_INTERNAL_CEF_ATOMICOPS_X86_GCC_H_\n\nstruct AtomicOps_x86CPUFeatureStruct {\n  bool has_amd_lock_mb_bug;\n};\n\nextern struct AtomicOps_x86CPUFeatureStruct AtomicOps_Internalx86CPUFeatures;\n\nnamespace base {\nnamespace subtle {\n\ninline Atomic32 NoBarrier_CompareAndSwap(volatile Atomic32* ptr,\n                                         Atomic32 old_value,\n                                         Atomic32 new_value) {\n  return __sync_val_compare_and_swap(ptr, old_value, new_value);\n}\n\ninline Atomic32 NoBarrier_AtomicExchange(volatile Atomic32* ptr,\n                                         Atomic32 new_value) {\n  return __sync_lock_test_and_set(ptr, new_value);\n}\n\ninline Atomic32 NoBarrier_AtomicIncrement(volatile Atomic32* ptr,\n                                          Atomic32 increment) {\n  return __sync_add_and_fetch(ptr, increment);\n}\n\ninline Atomic32 Barrier_AtomicIncrement(volatile Atomic32* ptr,\n                                        Atomic32 increment) {\n  return __sync_add_and_fetch(ptr, increment);\n}\n\ninline Atomic32 Acquire_CompareAndSwap(volatile Atomic32* ptr,\n                                       Atomic32 old_value,\n                                       Atomic32 new_value) {\n  return __sync_val_compare_and_swap(ptr, old_value, new_value);\n}\n\ninline Atomic32 Release_CompareAndSwap(volatile Atomic32* ptr,\n                                       Atomic32 old_value,\n                                       Atomic32 new_value) {\n  return __sync_val_compare_and_swap(ptr, old_value, new_value);\n}\n\ninline void MemoryBarrier() { __sync_synchronize(); }\n\ninline void NoBarrier_Store(volatile Atomic32* ptr, Atomic32 value) {\n  *ptr = value;\n}\n\ninline void Acquire_Store(volatile Atomic32* ptr, Atomic32 value) {\n  __sync_synchronize();\n  *ptr = value;\n}\n\ninline void Release_Store(volatile Atomic32* ptr, Atomic32 value) {\n  __sync_synchronize();\n  *ptr = value;\n}\n\ninline Atomic32 NoBarrier_Load(volatile const Atomic32* ptr) { return *ptr; }\n\ninline Atomic32 Acquire_Load(volatile const Atomic32* ptr) { return *ptr; }\n\ninline Atomic32 Release_Load(volatile const Atomic32* ptr) { return *ptr; }\n\n#ifdef ARCH_CPU_64_BITS\n\ninline Atomic64 NoBarrier_CompareAndSwap(volatile Atomic64* ptr,\n                                         Atomic64 old_value,\n                                         Atomic64 new_value) {\n  return __sync_val_compare_and_swap(ptr, old_value, new_value);\n}\n\ninline Atomic64 NoBarrier_AtomicExchange(volatile Atomic64* ptr,\n                                         Atomic64 new_value) {\n  return __sync_lock_test_and_set(ptr, new_value);\n}\n\ninline Atomic64 NoBarrier_AtomicIncrement(volatile Atomic64* ptr,\n                                          Atomic64 increment) {\n  return __sync_add_and_fetch(ptr, increment);\n}\n\ninline Atomic64 Barrier_AtomicIncrement(volatile Atomic64* ptr,\n                                        Atomic64 increment) {\n  return __sync_add_and_fetch(ptr, increment);\n}\n\ninline Atomic64 Acquire_CompareAndSwap(volatile Atomic64* ptr,\n                                       Atomic64 old_value,\n                                       Atomic64 new_value) {\n  return __sync_val_compare_and_swap(ptr, old_value, new_value);\n}\n\ninline Atomic64 Release_CompareAndSwap(volatile Atomic64* ptr,\n                                       Atomic64 old_value,\n                                       Atomic64 new_value) {\n  return __sync_val_compare_and_swap(ptr, old_value, new_value);\n}\n\ninline void NoBarrier_Store(volatile Atomic64* ptr, Atomic64 value) {\n  *ptr = value;\n}\n\ninline void Acquire_Store(volatile Atomic64* ptr, Atomic64 value) {\n  __sync_synchronize();\n  *ptr = value;\n}\n\ninline void Release_Store(volatile Atomic64* ptr, Atomic64 value) {\n  __sync_synchronize();\n  *ptr = value;\n}\n\ninline Atomic64 NoBarrier_Load(volatile const Atomic64* ptr) { return *ptr; }\n\ninline Atomic64 Acquire_Load(volatile const Atomic64* ptr) { return *ptr; }\n\ninline Atomic64 Release_Load(volatile const Atomic64* ptr) { return *ptr; }\n\n#endif  // ARCH_CPU_64_BITS\n\n}  // namespace subtle\n}  // namespace base\n\n#endif  // CEF_INCLUDE_BASE_INTERNAL_CEF_ATOMICOPS_X86_GCC_H_\n'


def ensure_gcc_atomicops_header(cef_dir):
    """CEF minimal distribution lacks the GCC atomicops header - write it."""
    hdr = os.path.join(cef_dir, "include", "base", "internal",
                       "cef_atomicops_x86_gcc.h")
    if not os.path.exists(hdr):
        with open(hdr, "w", encoding="utf-8") as f:
            f.write(GCC_ATOMICOPS_HEADER)
        print("wrote cef_atomicops_x86_gcc.h")


def main():
    setup_toolchain()
    cef_dir = setup_cef()
    ensure_gcc_atomicops_header(cef_dir)
    build_helper(cef_dir)
    copy_runtime(cef_dir)
    print("ALL DONE")


if __name__ == "__main__":
    main()
