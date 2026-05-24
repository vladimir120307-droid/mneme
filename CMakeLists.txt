cmake_minimum_required(VERSION 3.18)
project(mneme_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# ── pybind11 ───────────────────────────────────────────────────────────
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# ── OpenMP (optional) ──────────────────────────────────────────────────
find_package(OpenMP)

# ── optimisation & SIMD flags ──────────────────────────────────────────
if(MSVC)
    add_compile_options(/O2 /fp:fast /arch:AVX2 /W4 /permissive-)
else()
    add_compile_options(
        -O3 -ffast-math -funroll-loops -fvisibility=hidden
        -Wall -Wextra -Wpedantic
    )
    include(CheckCXXCompilerFlag)
    check_cxx_compiler_flag(-mavx2 HAS_AVX2)
    if(HAS_AVX2)
        add_compile_options(-mavx2)
    endif()
endif()

# ── the extension module ───────────────────────────────────────────────
pybind11_add_module(_native MODULE
    native/src/vector_index.cpp
    native/src/scoring.cpp
    native/src/bindings.cpp
)

target_include_directories(_native PRIVATE native/include)

if(OpenMP_CXX_FOUND)
    target_link_libraries(_native PRIVATE OpenMP::OpenMP_CXX)
    target_compile_definitions(_native PRIVATE MNEME_HAVE_OPENMP=1)
endif()

# install the .so/.pyd alongside the Python package as mneme._native
install(TARGETS _native LIBRARY DESTINATION mneme)
