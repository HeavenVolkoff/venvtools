import re
import shutil
from os import path
from sys import argv
from distutils.log import INFO, _global_log

from setuptools import Command
from setuptools.config import read_configuration

from .extended_env_builder import ExtendedEnvBuilder

if path.basename(argv[0]) != "setup.py":
    raise EnvironmentError("Command entry point must be setup.py")

PROJECT_PATH = path.dirname(argv[0])

if not path.isfile(path.join(PROJECT_PATH, "setup.py")):
    raise FileNotFoundError(f"No setup.py found at project: {PROJECT_PATH}")

PROJECT_CONF = read_configuration(path.join(PROJECT_PATH, "setup.cfg"))


class VirtualEnvCommand(Command):
    description = "Build development virtual environment"
    user_options = [
        # The format is (long option, short option, description).
        (
            "env-name=",
            "n",
            "Virtual environment name. (DEFAULT: Current directory name)",
        ),
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
    ]

    # noinspection PyAttributeOutsideInit
    def initialize_options(self):
        # All options must be initialized as None due to ConfigParser
        self.path = ".venv"
        self.extras = ""
        self.get_pip = "https://bootstrap.pypa.io/get-pip.py"
        self.env_name = PROJECT_CONF["metadata"]["name"]
        self.system_site_packages = False

    # noinspection PyAttributeOutsideInit
    def finalize_options(self):
        if not self.env_name:
            raise TypeError("Virtual environment must have a name")

        if not self.get_pip:
            raise TypeError("Invalid get_pip.py url")

        this = self

        class SpecializedEnvBuilder(ExtendedEnvBuilder):
            def announce(self, msg):
                this.announce(msg, INFO)

        self.env_builder = SpecializedEnvBuilder(
            self.env_name,
            get_pip=self.get_pip,
            verbose=bool(_global_log.threshold <= INFO),
            project_path=PROJECT_PATH,
            project_extras=re.sub(r"\n+", ",", self.extras.strip()),
            system_site_packages=bool(self.system_site_packages),
        )

    def run(self):
        self.announce("Creating virtual env", INFO)

        egg_info = path.join(
            PROJECT_PATH, f"{PROJECT_CONF['metadata']['name']}.egg-info"
        )
        # Remove egg-info to allow package dependencies to be recalculated
        if path.isdir(egg_info):
            shutil.rmtree(egg_info)

        self.env_builder.create(self.path)
