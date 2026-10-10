"""05-event-driven/cpp/order-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp05EventDrivenCppOrderServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
        self.requires("libpq/17.11")
        self.requires("librdkafka/2.14.2")
