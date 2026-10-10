cmake_minimum_required(VERSION 3.31)
project(cndp-01-cloud-native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# The gcc-toolset-15 libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

# Static archives that depend on each other (Drogon, trantor, OpenTelemetry, ...):
# let the linker rescan the group.
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(PostgreSQL REQUIRED)
find_package(opentelemetry-cpp CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(order-service src/main.cpp)
target_include_directories(order-service PRIVATE src)
target_link_libraries(order-service PRIVATE
    Drogon::Drogon spdlog::spdlog PostgreSQL::PostgreSQL
    opentelemetry-cpp::opentelemetry-cpp Threads::Threads)
