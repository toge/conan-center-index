from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.microsoft import check_min_vs, is_msvc_static_runtime, is_msvc
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rm, rmdir, replace_in_file
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.scm import Version
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
import os

required_conan_version = ">=1.53.0"

class PrometheusCppConan(ConanFile):
    name = "prometheus-cpp"
    description = "Prometheus Client Library for Modern C++"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/jupp0r/prometheus-cpp"
    topics = ("metrics", "prometheus", "networking")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_pull": [True, False],
        "with_push": [True, False],
        "with_compression": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_pull": True,
        "with_push": True,
        "with_compression": True,
    }

    @property
    def _min_cppstd(self):
        return 11

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_pull:
            self.options.rm_safe("with_compression")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_pull:
            self.requires("civetweb/1.15")
        if self.options.with_push:
            self.requires("libcurl/7.86.0")
        if self.options.get_safe("with_compression"):
            self.requires("zlib/1.2.13")

    def validate(self):
        if self.info.settings.compiler.cppstd:
            check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["USE_THIRDPARTY_LIBRARIES"] = False
        tc.variables["ENABLE_TESTING"] = False
        tc.variables["OVERRIDE_CXX_STANDARD_FLAGS"] = not valid_min_cppstd(self, 11)
        tc.variables["ENABLE_PULL"] = self.options.with_pull
        tc.variables["ENABLE_PUSH"] = self.options.with_push
        if self.options.with_pull:
            tc.variables["ENABLE_COMPRESSION"] = self.options.with_compression
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "prometheus-cpp")

        self.cpp_info.components["prometheus-cpp-core"].set_property("cmake_target_name", "prometheus-cpp::core")
        self.cpp_info.components["prometheus-cpp-core"].set_property("pkg_config_name", "prometheus-cpp-core")
        self.cpp_info.components["prometheus-cpp-core"].libs = ["prometheus-cpp-core"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["prometheus-cpp-core"].system_libs = ["pthread", "rt"]

        if self.options.with_push:
            self.cpp_info.components["prometheus-cpp-push"].set_property("cmake_target_name", "prometheus-cpp::push")
            self.cpp_info.components["prometheus-cpp-push"].set_property("pkg_config_name", "prometheus-cpp-push")
            self.cpp_info.components["prometheus-cpp-push"].libs = ["prometheus-cpp-push"]
            self.cpp_info.components["prometheus-cpp-push"].requires = [
                "prometheus-cpp-core",
                "libcurl::libcurl",
            ]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["prometheus-cpp-push"].system_libs = ["pthread", "rt"]

        if self.options.with_pull:
            self.cpp_info.components["prometheus-cpp-pull"].set_property("cmake_target_name", "prometheus-cpp::pull")
            self.cpp_info.components["prometheus-cpp-pull"].set_property("pkg_config_name", "prometheus-cpp-pull")
            self.cpp_info.components["prometheus-cpp-pull"].libs = ["prometheus-cpp-pull"]
            self.cpp_info.components["prometheus-cpp-pull"].requires = [
                "prometheus-cpp-core",
                "civetweb::civetweb-cpp"
            ]
            if self.options.with_compression:
                self.cpp_info.components["prometheus-cpp-pull"].requires.append("zlib::zlib")
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["prometheus-cpp-pull"].system_libs = ["pthread", "rt"]

        # TODO: to remove in conan v2 once cmake_find_package* generators removed
        self.cpp_info.components["prometheus-cpp-core"].names["cmake_find_package"] = "core"
        self.cpp_info.components["prometheus-cpp-core"].names["cmake_find_package_multi"] = "core"
        if self.options.with_push:
            self.cpp_info.components["prometheus-cpp-push"].names["cmake_find_package"] = "push"
            self.cpp_info.components["prometheus-cpp-push"].names["cmake_find_package_multi"] = "push"
        if self.options.with_pull:
            self.cpp_info.components["prometheus-cpp-pull"].names["cmake_find_package"] = "pull"
            self.cpp_info.components["prometheus-cpp-pull"].names["cmake_find_package_multi"] = "pull"
