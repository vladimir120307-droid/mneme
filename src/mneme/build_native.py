"""Build helper: invokes CMake to compile the native core.

Usage:
    python -m mneme.build_native               # release build, install in-tree
    python -m mneme.build_native --debug
    python -m mneme.build_native --clean       # wipe build/ first

This is a convenience wrapper around CMake. It refuses to silently swallow
compiler errors — if your environment lacks a C++ toolchain, you'll see
the underlying message and can choose to keep using the pure-Python path.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # this file lives at <root>/src/mneme/build_native.py
    return Path(__file__).resolve().parents[2]


def _run(args: list[str], cwd: Path) -> None:
    print("$ " + " ".join(args), flush=True)
    res = subprocess.run(args, cwd=cwd)
    if res.returncode != 0:
        sys.exit(res.returncode)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build Mneme's native core.")
    parser.add_argument("--debug", action="store_true", help="Build with debug info.")
    parser.add_argument("--clean", action="store_true", help="Remove build/ first.")
    parser.add_argument(
        "--jobs", "-j", type=int, default=0, help="Parallel build jobs (0 = auto)."
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    build = root / "build"
    if args.clean and build.exists():
        shutil.rmtree(build)

    cfg = "Debug" if args.debug else "Release"
    _run(
        [
            "cmake",
            "-S", str(root),
            "-B", str(build),
            f"-DCMAKE_BUILD_TYPE={cfg}",
            f"-DPython_EXECUTABLE={sys.executable}",
        ],
        cwd=root,
    )
    build_cmd = ["cmake", "--build", str(build), "--config", cfg]
    if args.jobs:
        build_cmd += ["-j", str(args.jobs)]
    else:
        build_cmd += ["-j"]
    _run(build_cmd, cwd=root)
    _run(
        ["cmake", "--install", str(build), "--prefix", str(root / "src"), "--config", cfg],
        cwd=root,
    )
    print("\n✓ Native core installed at src/mneme/_native.*")


if __name__ == "__main__":
    main()
