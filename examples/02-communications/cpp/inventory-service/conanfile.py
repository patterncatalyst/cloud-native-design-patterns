"""02-communications/cpp/inventory-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp02CommunicationsCppInventoryServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
    }

    def requirements(self):
        self.requires("grpc/1.84.0")
        self.requires("protobuf/6.33.5")
