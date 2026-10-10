cmake_minimum_required(VERSION 3.31)
project(stream-processor LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

find_package(RdKafka CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(Threads REQUIRED)

# __int128 is a GNU extension type; -Wpedantic would flag it, so it is not enabled.
add_executable(stream-processor src/main.cpp)
target_include_directories(stream-processor PRIVATE src)
target_link_libraries(stream-processor PRIVATE
    RdKafka::rdkafka++ nlohmann_json::nlohmann_json spdlog::spdlog Threads::Threads)

# Unit tests for window math, money rounding and event parsing (run by ctest in the image build).
enable_testing()
add_executable(aggregation_test tests/aggregation_test.cpp)
target_include_directories(aggregation_test PRIVATE src)
target_link_libraries(aggregation_test PRIVATE nlohmann_json::nlohmann_json)
add_test(NAME aggregation COMMAND aggregation_test)
