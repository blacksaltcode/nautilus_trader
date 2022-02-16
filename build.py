#!/usr/bin/env python3

import glob
import itertools
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np
from Cython.Build import build_ext
from Cython.Build import cythonize
from Cython.Compiler import Options
from Cython.Compiler.Version import version as cython_compiler_version
from setuptools import Distribution
from setuptools import Extension


# The Cargo rustc mode
CARGO_MODE = os.getenv("CARGO_MODE", "")
# If DEBUG mode is enabled, include traces necessary for coverage, profiling and skip optimizations
DEBUG_MODE = bool(os.getenv("DEBUG_MODE", ""))
# If ANNOTATION mode is enabled, generate an annotated HTML version of the input source files
ANNOTATION_MODE = bool(os.getenv("ANNOTATION_MODE", ""))
# If PARALLEL build is enabled, uses all CPUs for compile stage of build
PARALLEL_BUILD = True if os.getenv("PARALLEL_BUILD", "true") == "true" else False
# If SKIP_BUILD_COPY is enabled, prevents copying built *.so files back into the source tree
SKIP_BUILD_COPY = bool(os.getenv("SKIP_BUILD_COPY", ""))


################################################################################
#  RUST BUILD                                                                  #
################################################################################
# Directories with headers to include
RUST_INCLUDES = glob.glob("nautilus_core/*/")
RUST_LIBS_DIR = "debug" if CARGO_MODE in ("", "debug") else "release"
RUST_LIBS = [
    f"nautilus_core/target/{RUST_LIBS_DIR}/libnautilus_core.a",
    f"nautilus_core/target/{RUST_LIBS_DIR}/libnautilus_model.a",
]


def _build_rust_libs() -> None:
    # Build the Rust libraries using Cargo
    print("Compiling Rust libraries...")
    os.system(f"(cd nautilus_core && cargo build {CARGO_MODE})")  # noqa


################################################################################
#  CYTHON BUILD                                                                #
################################################################################
# https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html

Options.docstrings = True  # Include docstrings in modules
Options.fast_fail = True  # Abort the compilation on the first error occurred
Options.emit_code_comments = True
Options.annotate = ANNOTATION_MODE  # Create annotated HTML files for each .pyx
if ANNOTATION_MODE:
    Options.annotate_coverage_xml = "coverage.xml"
Options.fast_fail = True  # Abort compilation on first error
Options.warning_errors = True  # Treat compiler warnings as errors
Options.extra_warnings = True

CYTHON_COMPILER_DIRECTIVES = {
    "language_level": "3",
    "cdivision": True,  # If division is as per C with no check for zero (35% speed up)
    "embedsignature": True,  # If docstrings should be embedded into C signatures
    "profile": DEBUG_MODE,  # If we're debugging, turn on profiling
    "linetrace": DEBUG_MODE,  # If we're debugging, turn on line tracing
    "warn.maybe_uninitialized": True,
}


def _build_extensions() -> List[Extension]:
    # Regarding the compiler warning: #warning "Using deprecated NumPy API,
    # disable it with " "#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION"
    # https://stackoverflow.com/questions/52749662/using-deprecated-numpy-api
    # From the Cython docs: "For the time being, it is just a warning that you can ignore."
    define_macros = [("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
    if DEBUG_MODE or ANNOTATION_MODE:
        # Profiling requires special macro directives
        define_macros.append(("CYTHON_TRACE", "1"))

    extra_compile_args = []
    if not DEBUG_MODE and platform.system() != "Windows":
        extra_compile_args.append("-O3")
        extra_compile_args.append("-pipe")

    print("Creating C extension modules...")
    print(f"define_macros={define_macros}")
    print(f"extra_compile_args={extra_compile_args}")

    return [
        Extension(
            name=str(pyx.relative_to(".")).replace(os.path.sep, ".")[:-4],
            sources=[str(pyx)],
            include_dirs=[".", np.get_include()] + RUST_INCLUDES,
            define_macros=define_macros,
            language="c",
            extra_link_args=RUST_LIBS,
            extra_compile_args=extra_compile_args,
        )
        for pyx in itertools.chain(Path("nautilus_trader").rglob("*.pyx"))
    ]


def _build_distribution(extensions: List[Extension]) -> Distribution:
    # Build a Distribution using cythonize()
    # Determine the build output directory
    if DEBUG_MODE:
        # For subsequent debugging, the C source needs to be in
        # the same tree as the Cython code (not in a separate build directory).
        build_dir = None
    elif ANNOTATION_MODE:
        build_dir = "build/annotated"
    else:
        build_dir = "build/optimized"

    distribution = Distribution(
        dict(
            name="nautilus_trader",
            ext_modules=cythonize(
                module_list=extensions,
                compiler_directives=CYTHON_COMPILER_DIRECTIVES,
                nthreads=os.cpu_count(),
                build_dir=build_dir,
                gdb_debug=DEBUG_MODE,
            ),
            zip_safe=False,
        )
    )
    distribution.package_dir = "nautilus_trader"
    return distribution


def _copy_build_dir_to_project(cmd: build_ext) -> None:
    # Copy built extensions back to the project tree
    for output in cmd.get_outputs():
        relative_extension = os.path.relpath(output, cmd.build_lib)
        if not os.path.exists(output):
            continue

        # Copy the file and set permissions
        shutil.copyfile(output, relative_extension)
        mode = os.stat(relative_extension).st_mode
        mode |= (mode & 0o444) >> 2
        os.chmod(relative_extension, mode)

    print("Copied all compiled '.so' dynamic library files into source")


def build() -> None:
    """Construct the extensions and distribution."""  # noqa
    _build_rust_libs()

    # Create C Extensions to feed into cythonize()
    extensions = _build_extensions()
    distribution = _build_distribution(extensions)

    # Build and run the command
    print("Compiling C extension modules...")
    cmd: build_ext = build_ext(distribution)
    if PARALLEL_BUILD:
        cmd.parallel = os.cpu_count()
    cmd.ensure_finalized()
    cmd.run()

    if not SKIP_BUILD_COPY:
        # Copy the build back into the project for development and packaging
        _copy_build_dir_to_project(cmd)


if __name__ == "__main__":
    print("\033[36m")
    print("=====================================================================")
    print("Nautilus Builder")
    print("=====================================================================\033[0m")

    ts_start = datetime.utcnow()

    # Work around a Cython problem in Python 3.8.x on macOS
    # https://github.com/cython/cython/issues/3262
    if platform.system() == "Darwin":
        print("macOS: Setting multiprocessing method to 'fork'.")
        try:
            # noinspection PyUnresolvedReferences
            import multiprocessing

            multiprocessing.set_start_method("fork", force=True)
        except ImportError:  # pragma: no cover
            print("multiprocessing not available")

    # Note: On macOS (and perhaps other platforms), executable files may be
    # universal files containing multiple architectures. To determine the
    # “64-bitness” of the current interpreter, it is more reliable to query the
    # sys.maxsize attribute:
    bits = "64-bit" if sys.maxsize > 2 ** 32 else "32-bit"
    rustc_version = subprocess.check_output(["rustc", "--version"])  # noqa
    print(f"System: {platform.system()} {bits}")
    print(f"Rust:   {rustc_version.lstrip(b'rustc ').decode()[:-1]}")
    print(f"Python: {platform.python_version()}")
    print(f"Cython: {cython_compiler_version}")
    print(f"NumPy:  {np.__version__}")
    print("")

    print("Starting build...")
    print(f"CARGO_MODE={CARGO_MODE}")
    print(f"DEBUG_MODE={DEBUG_MODE}")
    print(f"ANNOTATION_MODE={ANNOTATION_MODE}")
    print(f"PARALLEL_BUILD={PARALLEL_BUILD}")
    print(f"SKIP_BUILD_COPY={SKIP_BUILD_COPY}")
    print("")

    build()
    print(f"Build time: {datetime.utcnow() - ts_start}")
    print("\033[32m" + "Build completed" + "\033[0m")
