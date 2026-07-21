"""examples/01-cloud-native-principles/cpp — Conan 2 recipe.

Drogon-based REST service demonstrating cloud-native principles. Uses libpq
(PostgreSQL C client) installed from UBI's AppStream as a system package,
not via Conan, to avoid libpqxx Conan recipe issues and simplify the runtime
image.

Dependencies:
- Drogon (REST framework with jsoncpp for JSON)
- spdlog (structured logging)
- libpq (system package, not from Conan)
"""

from conan import ConanFile


class CloudNative01Conan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        # Static linkage everywhere for a portable runtime image.
        "*/*:shared": False,
        # OpenSSL FIPS skipped (Digest::SHA on UBI 9 without EPEL).
        "openssl/*:no_fips": True,
    }

    def requirements(self):
        # Drogon REST framework (includes jsoncpp for JSON responses)
        self.requires("drogon/1.9.8")
        # Structured logging
        self.requires("spdlog/1.15.0")
