import os
import functools
from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration

required_conan_version = ">=1.43.0"


class ConanRecipe(ConanFile):
    name = "catch2"
    description = "A modern, C++-native, header-only, framework for unit-tests, TDD and BDD"
    topics = ("conan", "catch2", "header-only", "unit-test", "tdd", "bdd")
    license = "BSL-1.0"
    homepage = "https://github.com/catchorg/Catch2"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "with_main": [True, False],
        "with_benchmark": [True, False],
        "with_prefix": [True, False],
        "default_reporter": "ANY",
    }
    default_options = {
        "fPIC": True,
        "with_main": False,
        "with_benchmark": False,
        "with_prefix": False,
        "default_reporter": None,
    }
    generators = "cmake"

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    @property
    def _default_reporter_str(self):
        return '"{}"'.format(str(self.options.default_reporter).strip('"'))

    def export_sources(self):
        self.copy("CMakeLists.txt")
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            self.copy(patch["patch_file"])

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if tools.Version(self.version) >= "3.0.0":
            del self.options.with_main

    def configure(self):
        if not self.options.get_safe("with_main") and tools.Version(self.version) < "3.0.0":
            del self.options.fPIC
            del self.options.with_benchmark

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "7",
            "Visual Studio": "15",
            "clang": "5",
            "apple-clang": "10",
        }

    def validate(self):
        if tools.Version(self.version) < "2.13.1" and self.settings.arch == "armv8":
            raise ConanInvalidConfiguration("ARMv8 is supported by 2.13.1+ only! give up!")
        if self.options.get_safe("with_main") and tools.Version(self.version) < "2.13.4":
            raise ConanInvalidConfiguration("Option with_main not supported with versions < 2.13.4")

        if tools.Version(self.version) < "3.0.0":
            if self.settings.compiler.get_safe("cppstd"):
                tools.check_min_cppstd(self, "11")
        else:
            if self.settings.compiler.get_safe("cppstd"):
                tools.check_min_cppstd(self, "14")
            minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
            if minimum_version:
                if tools.Version(self.settings.compiler.version) < minimum_version:
                    raise ConanInvalidConfiguration("structopt: Unsupported compiler: {}-{} "
                                                    "(https://github.com/p-ranav/structopt#compiler-compatibility)."
                                                    .format(self.settings.compiler, self.settings.compiler.version))
            else:
                self.output.warn("{} requires C++14. Your compiler is unknown. Assuming it supports C++14.".format(self.name))

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder)

    @functools.lru_cache(1)
    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["BUILD_TESTING"] = "OFF"
        cmake.definitions["CATCH_INSTALL_DOCS"] = "OFF"
        cmake.definitions["CATCH_INSTALL_HELPERS"] = "ON"
        if tools.Version(self.version) < "3.0.0":
            cmake.definitions["CATCH_BUILD_STATIC_LIBRARY"] = self.options.get_safe("with_main")
        cmake.definitions["enable_benchmark"] = self.options.get_safe("with_benchmark", False)
        cmake.definitions["CATCH_CONFIG_PREFIX_ALL"] = self.options.with_prefix
        if self.options.default_reporter:
            cmake.definitions["CATCH_CONFIG_DEFAULT_REPORTER"] = self._default_reporter_str
        if tools.Version(self.version) < "3.0.0":
            cmake.definitions["CMAKE_CXX_STANDARD"] = 11
        else:
            cmake.definitions["CMAKE_CXX_STANDARD"] = 14

        cmake.configure(build_folder=self._build_subfolder)
        return cmake

    def _patch_sources(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)

    def build(self):
        self._patch_sources()
        if tools.Version(self.version) < "3.0.0":
            # Catch2 does skip install if included as subproject:
            # https://github.com/catchorg/Catch2/blob/79a5cd795c387e2da58c13e9dcbfd9ea7a2cfb30/CMakeLists.txt#L100-L102
            main_cml = os.path.join(self._source_subfolder, "CMakeLists.txt")
            tools.replace_in_file(main_cml, "if (NOT_SUBPROJECT)", "if (TRUE)")

        if self.options.get_safe("with_main") or tools.Version(self.version) >= "3.0.0":
            cmake = self._configure_cmake()
            cmake.build()

    def package(self):
        self.copy(pattern="LICENSE.txt", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "share"))
        for cmake_file in ["ParseAndAddCatchTests.cmake", "Catch.cmake", "CatchAddTests.cmake"]:
            self.copy(
                cmake_file,
                src=os.path.join(self._source_subfolder, "contrib"),
                dst=os.path.join("lib", "cmake", "Catch2"),
            )

    def package_id(self):
        if not self.options.get_safe("with_main") and tools.Version(self.version) < "3.0.0":
            self.info.header_only()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Catch2")
        self.cpp_info.set_property("cmake_target_name",
            "Catch2::Catch2{}".format("WithMain" if self.options.get_safe("with_main") else ""))
        self.cpp_info.names["cmake_find_package"] = "Catch2"
        self.cpp_info.names["cmake_find_package_multi"] = "Catch2"

        if self.options.get_safe("with_main") or tools.Version(self.version) >= "3.0.0":
            self.cpp_info.components["Catch2"].set_property("cmake_target_name", "Catch2::Catch2")
            self.cpp_info.components["Catch2"].names["cmake_find_package"] = "Catch2"
            self.cpp_info.components["Catch2"].names["cmake_find_package_multi"] = "Catch2"
            if tools.Version(self.version) >= "3.0.0":
                self.cpp_info.components["Catch2"].libs = ["Catch2"]

            self.cpp_info.components["Catch2WithMain"].builddirs = [os.path.join("lib", "cmake", "Catch2")]
            if tools.Version(self.version) >= "3.0.0":
                self.cpp_info.components["Catch2WithMain"].libs = ["Catch2Main"]
                self.cpp_info.components["Catch2WithMain"].requires = ["Catch2"]
            else:
                self.cpp_info.components["Catch2WithMain"].libs = ["Catch2WithMain"]
            self.cpp_info.components["Catch2WithMain"].system_libs = ["log"] if self.settings.os == "Android" else []
            self.cpp_info.components["Catch2WithMain"].set_property("cmake_target_name", "Catch2::Catch2WithMain")
            self.cpp_info.components["Catch2WithMain"].names["cmake_find_package"] = "Catch2WithMain"
            self.cpp_info.components["Catch2WithMain"].names["cmake_find_package_multi"] = "Catch2WithMain"
            defines = self.cpp_info.components["Catch2WithMain"].defines
        else:
            self.cpp_info.builddirs = [os.path.join("lib", "cmake", "Catch2")]
            self.cpp_info.system_libs = ["log"] if self.settings.os == "Android" else []
            defines = self.cpp_info.defines

        if self.options.get_safe("with_benchmark", False):
            defines.append("CATCH_CONFIG_ENABLE_BENCHMARKING")
        if self.options.with_prefix:
            defines.append("CATCH_CONFIG_PREFIX_ALL")
        if self.options.default_reporter:
            defines.append("CATCH_CONFIG_DEFAULT_REPORTER={}".format(self._default_reporter_str))
