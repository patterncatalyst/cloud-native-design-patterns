"""24-monolith-to-microservices/cpp/router: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp24MonolithToMicroservicesCppRouterConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
