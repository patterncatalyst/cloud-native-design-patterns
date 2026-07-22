cmake_minimum_required(VERSION 3.25)
project(flag-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(gRPC CONFIG REQUIRED)
find_package(protobuf CONFIG REQUIRED)
find_package(Threads REQUIRED)

# Generate protobuf messages only (no gRPC service stubs — flagd's service
# is named "Service" which causes a C++ name collision in codegen)
set(PROTO_FILE ${CMAKE_CURRENT_SOURCE_DIR}/proto/schema.proto)
set(PROTO_OUT ${CMAKE_CURRENT_BINARY_DIR}/proto)
file(MAKE_DIRECTORY ${PROTO_OUT})

add_custom_command(
    OUTPUT ${PROTO_OUT}/schema.pb.cc ${PROTO_OUT}/schema.pb.h
    COMMAND protobuf::protoc
        --proto_path=${CMAKE_CURRENT_SOURCE_DIR}/proto
        --cpp_out=${PROTO_OUT}
        ${PROTO_FILE}
    DEPENDS ${PROTO_FILE} protobuf::protoc
)

add_executable(flag-service
    src/main.cpp
    ${PROTO_OUT}/schema.pb.cc
)

target_include_directories(flag-service PRIVATE ${PROTO_OUT})

target_link_libraries(flag-service PRIVATE
    Drogon::Drogon gRPC::grpc++ protobuf::protobuf Threads::Threads)
