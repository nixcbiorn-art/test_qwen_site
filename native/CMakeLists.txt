cmake_minimum_required(VERSION 3.15)
project(MarketMonitorCore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Оптимизации для производительности
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    if(MSVC)
        add_compile_options(/O2 /arch:AVX2)
    else()
        add_compile_options(-O3 -march=native -mtune=native)
    endif()
endif()

# Поиск Python
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Поиск pybind11
find_package(pybind11 CONFIG QUIET)
if(NOT pybind11_FOUND)
    # Fallback: используем FetchContent для загрузки pybind11
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.11.1
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# Библиотека технических индикаторов (C++)
add_library(native_indicators SHARED
    src/indicators.cpp
)
target_include_directories(native_indicators PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Библиотека детектора изменений (C++)
add_library(native_detector SHARED
    src/detector.cpp
)
target_include_directories(native_detector PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Python bindings через pybind11
pybind11_add_module(native_bindings bindings/bindings.cpp)
target_link_libraries(native_bindings PRIVATE 
    native_indicators 
    native_detector
)

# Установка библиотек
install(TARGETS native_indicators native_detector native_bindings
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)
