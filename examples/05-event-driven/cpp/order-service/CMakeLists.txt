cmake_minimum_required(VERSION 3.31)
project(order-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

# Static archives that depend on each other (Drogon, librdkafka, OpenTelemetry): let the linker rescan the group.
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(RdKafka CONFIG REQUIRED)  # librdkafka C++ API (rdkafka++) from Conan
find_package(PostgreSQL REQUIRED)      # libpq from Conan (direct C client)
find_package(spdlog CONFIG REQUIRED)
find_package(opentelemetry-cpp CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(order-service src/main.cpp)
target_include_directories(order-service PRIVATE src)
target_link_libraries(order-service PRIVATE
    Drogon::Drogon RdKafka::rdkafka++ PostgreSQL::PostgreSQL spdlog::spdlog
    opentelemetry-cpp::opentelemetry-cpp Threads::Threads)
