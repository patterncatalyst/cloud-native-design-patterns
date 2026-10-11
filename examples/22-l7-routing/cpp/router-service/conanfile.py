"""examples/22-l7-routing/cpp/router-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
sol2 binds Lua 5.4. sol2 3.5.0's recipe pins lua/5.4.6, so the newest 5.4 release is
forced with an override.
"""

from conan import ConanFile


class Cndp22RouterConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
        self.requires("sol2/3.5.0")
        self.requires("lua/5.4.8", override=True)
        self.requires("jsoncpp/1.9.8", override=True)  # drogon pins jsoncpp 1.9.5
        self.requires("util-linux-libuuid/2.41.2", override=True)  # drogon pins util-linux-libuuid 2.39.2
