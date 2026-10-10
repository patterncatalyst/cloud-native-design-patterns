"""Local Conan recipe for cppgraphqlgen (microsoft/cppgraphqlgen), which is not on ConanCenter.

Builds the runtime libraries (graphqlpeg, graphqlresponse, graphqlservice) as static archives.
JSON handling stays with the host application (jsoncpp from Drogon), so RapidJSON and
graphqljson are off. The schemagen code generator is an option (`-o cppgraphqlgen/*:schemagen=True`),
only used to regenerate the committed schema sources; it pulls Boost.program_options.
"""

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir


class CppGraphQLGenConan(ConanFile):
    name = "cppgraphqlgen"
    version = "4.5.9"
    license = "MIT"
    url = "https://github.com/microsoft/cppgraphqlgen"
    description = "C++ GraphQL schema service generator (schemagen) and runtime"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False], "schemagen": [True, False]}
    default_options = {"fPIC": True, "schemagen": False}

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("taocpp-pegtl/3.2.8", transitive_headers=True)
        if self.options.schemagen:
            self.requires("boost/1.90.0")

    def validate(self):
        check_min_cppstd(self, 20)

    def configure(self):
        if self.options.schemagen:
            # schemagen only needs Boost.program_options (Boost.process, pulled in by the recipe, wants
            # context and filesystem, so those two stay on).
            for comp in ("charconv", "cobalt", "contract",
                         "coroutine", "fiber", "graph",
                         "graph_parallel", "iostreams", "json", "locale", "log", "math", "mpi",
                         "nowide", "python", "random", "regex", "serialization", "stacktrace",
                         "test", "timer", "type_erasure", "url", "wave"):
                setattr(self.options["boost"], f"without_{comp}", True)

    def source(self):
        get(self, "https://github.com/microsoft/cppgraphqlgen/archive/refs/tags/v4.5.9.tar.gz",
            sha256="65a7c80bbc98f913bf1fb0647262b696fdf53baa4f1b990fe741de29e07884ac",
            strip_root=True)
        # GCC 15 is stricter than the project's CI; keep the warnings, drop -Werror.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "-Wall -Wextra -pedantic -Werror", "-Wall -Wextra -pedantic")
        # C++23 deprecates the space in `operator"" _graphql`.
        for rel in ("include/graphqlservice/GraphQLParse.h", "src/SyntaxTree.cpp"):
            replace_in_file(self, os.path.join(self.source_folder, rel), 'operator"" _graphql', 'operator""_graphql')

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # option() runs before project(), so these must be -D cache variables.
        tc.cache_variables["GRAPHQL_BUILD_SCHEMAGEN"] = bool(self.options.schemagen)
        tc.cache_variables["GRAPHQL_BUILD_CLIENTGEN"] = False
        tc.cache_variables["GRAPHQL_BUILD_TESTS"] = False
        tc.cache_variables["GRAPHQL_USE_RAPIDJSON"] = False
        tc.cache_variables["GRAPHQL_UPDATE_SAMPLES"] = False
        tc.cache_variables["GRAPHQL_UPDATE_VERSION"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        CMake(self).install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cppgraphqlgen")
        self.cpp_info.set_property("cmake_target_name", "cppgraphqlgen::cppgraphqlgen")
        self.cpp_info.components["graphqlpeg"].libs = ["graphqlpeg"]
        self.cpp_info.components["graphqlpeg"].requires = ["taocpp-pegtl::taocpp-pegtl"]
        self.cpp_info.components["graphqlresponse"].libs = ["graphqlresponse"]
        self.cpp_info.components["graphqlservice"].libs = ["graphqlservice"]
        self.cpp_info.components["graphqlservice"].requires = ["graphqlpeg", "graphqlresponse"]
        for comp in ("graphqlpeg", "graphqlresponse", "graphqlservice"):
            self.cpp_info.components[comp].set_property("cmake_target_name", f"cppgraphqlgen::{comp}")
            if self.settings.os in ("Linux", "FreeBSD"):
                self.cpp_info.components[comp].system_libs.append("pthread")
        if self.options.schemagen:
            self.cpp_info.ignored_requires = ["boost"]  # only the schemagen executable uses it
            self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
