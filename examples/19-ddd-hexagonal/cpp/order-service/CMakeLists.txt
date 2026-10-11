cmake_minimum_required(VERSION 3.31)
project(cndp-19-ddd-hexagonal LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)

# Force --start-group/--end-group around static archives to resolve
# circular dependencies among Drogon's transitive deps (jsoncpp, trantor, etc.)
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(PostgreSQL REQUIRED)  # libpq from Conan (the direct C client)
find_package(Threads REQUIRED)

# REST service binary (main HTTP server)
add_executable(order-service
    src/main.cpp
    src/adapters/rest_adapter.cpp
)
target_include_directories(order-service PRIVATE src)
target_link_libraries(order-service PRIVATE
    Drogon::Drogon spdlog::spdlog PostgreSQL::PostgreSQL Threads::Threads)

# CLI binary (separate driving adapter)
add_executable(cli-place-order src/cli_main.cpp)
target_include_directories(cli-place-order PRIVATE src)
target_link_libraries(cli-place-order PRIVATE
    spdlog::spdlog PostgreSQL::PostgreSQL Threads::Threads)
