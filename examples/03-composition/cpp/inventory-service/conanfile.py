"""03-composition/cpp/inventory-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp03CompositionCppInventoryServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
    }

    def requirements(self):
        self.requires("grpc/1.84.0")
        self.requires("protobuf/6.33.5")
        self.requires("spdlog/1.17.0")
        self.requires("fmt/12.2.0", override=True)  # spdlog pins fmt 12.1.0
