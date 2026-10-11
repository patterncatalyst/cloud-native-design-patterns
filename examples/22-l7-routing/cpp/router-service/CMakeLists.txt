cmake_minimum_required(VERSION 3.31)
project(router-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

# Static archives that depend on each other (Drogon, trantor, ...): rescan the group.
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(sol2 CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(router-service src/main.cpp)
target_include_directories(router-service PRIVATE src)
target_link_libraries(router-service PRIVATE Drogon::Drogon sol2::sol2 Threads::Threads)

enable_testing()
add_executable(engine-test tests/engine_test.cpp)
target_include_directories(engine-test PRIVATE src)
target_link_libraries(engine-test PRIVATE sol2::sol2 Threads::Threads)
add_test(NAME engine COMMAND engine-test)
