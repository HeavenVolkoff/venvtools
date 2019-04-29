# Internal
import re
import shutil
import typing as T
from os import path
from sys import argv
from distutils.log import INFO, WARN, DEBUG, _global_log

# External
from setuptools import Command
from pkg_resources import parse_requirements

# Project
from .extended_env_builder import ExtendedEnvBuilder

if path.basename(argv[0]) != "setup.py":
    raise EnvironmentError("Command entry point must be setup.py")

PROJECT_PATH = path.dirname(path.abspath(argv[0]))

if not path.isfile(path.join(PROJECT_PATH, "setup.py")):
    raise FileNotFoundError(f"No setup.py found at project: {PROJECT_PATH}")


class VirtualEnvCommand(Command):
    description = "Build development virtual environment"
    user_options = [
        # The format is (long option, short option, description).
        ("env-name=", "n", "Virtual environment name. (DEFAULT: Project name)"),
        (
            "get-pip=",
            None,
            "Virtual env get-pip.py URL. (DEFAULT: https://bootstrap.pypa.io/get-pip.py)",
        ),
        ("extras=", "e", "Comma separated list of extras to be installed."),
        (
            "system-site-packages",
            None,
            "Make the system (global) site-packages dir available to the created environment.",
        ),
        ("rm", None, "Remove virtual environment."),
        ("editable", None, "Install package to venv as editable."),
        ("location", "l", "Retrieve virtual environment location."),
    ]

    def _get_req(self):
        requirements = []
        requirements.extend(self.distribution.install_requires)

        if self.extras:
            for extra in self.extras.split(","):
                requirements.extend(self.distribution.extras_require[extra])

        return tuple(parse_requirements(requirements))

    # noinspection PyAttributeOutsideInit
    def initialize_options(self):
        # All options are initialized as None due to ConfigParser
        self.rm = False
        self.path = ".venv"
        self.extras = ""
        self.get_pip = "https://bootstrap.pypa.io/get-pip.py"
        self.location = False
        self.editable = False
        self.env_name = self.distribution.metadata.name
        self.system_site_packages = False

    # noinspection PyAttributeOutsideInit
    def finalize_options(self):
        if not self.env_name:
            raise TypeError("Virtual environment must have a name")

        if not self.get_pip:
            raise TypeError("Invalid get_pip.py url")

        if self.distribution.dependency_links:
            raise RuntimeError("Dependency links are not supported anymore")

        self.extras = re.sub(r"\s*\n+\s*", ",", self.extras.strip())

    def run(self):
        if self.rm:
            if path.isdir(self.path):
                self.announce(f"Removing virtual env: {self.path}", INFO)
                shutil.rmtree(self.path)
            else:
                self.announce(f"There is no virtual env to remove", WARN)
            return

        if self.location:
            # TODO: Check if python is working
            if path.isdir(self.path):
                print(self.path)
            else:
                raise EnvironmentError("There is no virtual environment")
            return

        self.announce(f"Creating virtual env: {self.path}", INFO)

        egg_info_path = path.join(PROJECT_PATH, self.get_finalized_command("egg_info").egg_info)

        # Remove egg-info to allow package dependencies to be recalculated
        if path.isdir(egg_info_path):
            shutil.rmtree(egg_info_path)

        this = self

        class SpecializedEnvBuilder(ExtendedEnvBuilder):
            def announce(self, msg):
                this.announce(msg, INFO)

        SpecializedEnvBuilder(
            self.distribution.metadata.name,
            self.env_name,
            PROJECT_PATH,
            rm_main=not (
                bool(
                    [req for req in self._get_req() if req.name == self.distribution.metadata.name]
                )
            ),
            get_pip=self.get_pip,
            editable=self.editable,
            verbose=bool(_global_log.threshold <= DEBUG),
            project_extras=self.extras,
            setup_requires=self.distribution.setup_requires,
            system_site_packages=bool(self.system_site_packages),
        ).create(self.path)
