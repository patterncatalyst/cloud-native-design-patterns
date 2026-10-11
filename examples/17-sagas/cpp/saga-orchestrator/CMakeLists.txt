cmake_minimum_required(VERSION 3.31)
project(saga-orchestrator LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

# Static archives that depend on each other (Drogon, trantor, libpq, ...): rescan the group.
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(PostgreSQL REQUIRED)  # libpq from Conan (the direct C client)
find_package(sml CONFIG REQUIRED)  # boost::sml, standalone

add_executable(saga-orchestrator src/main.cpp)
target_include_directories(saga-orchestrator PRIVATE src)
target_link_libraries(saga-orchestrator PRIVATE Drogon::Drogon PostgreSQL::PostgreSQL sml::sml)

enable_testing()
add_executable(saga-test tests/saga_test.cpp)
target_include_directories(saga-test PRIVATE src)
target_link_libraries(saga-test PRIVATE sml::sml)
add_test(NAME saga COMMAND saga-test)
