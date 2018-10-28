#!/usr/bin/env python3

from setuptools import setup, Command
from distutils import log


# noinspection PyPep8Naming
class VirtualEnvCommand(Command):
    description = 'run Pylint on Python source files'
    user_options = [
        # The format is (long option, short option, description).
        ('venv-path=', None, 'path where venv will be installed'),
        ('extras=', 'e', 'comma separated list of extras to be installed'),
    ]

    def initialize_options(self):
        self.extras = None
        self.activate = False
        self.venv_path = ".venv"
        self.deactivate = False
        self.ensure_pip = False
        self.get_pip_url = "https://bootstrap.pypa.io/get-pip.py"

    def finalize_options(self):
        import sys

        if not self.get_pip_url:
            self.ensure_pip = True

        self.init_venv_args = [sys.executable, "-m", "venv", self.venv_path]

        if not self.ensure_pip:
            self.init_venv_args.append("--without-pip")

    def run(self):
        import os
        import subprocess
        import urllib.request

        # TODO: Check if venv is already created
        self.announce("Creating venv",log.INFO)
        subprocess.run(self.init_venv_args, check=True)

        if not self.ensure_pip:
            self.announce("Installing pip",log.INFO)
            with urllib.request.urlopen(self.get_pip_url) as response:
                subprocess.run([os.path.join(self.venv_path, "bin", "python"), "-"], input=response.read(), check=True)

        self.announce("Installing package dependencies", log.INFO)
        subprocess.run([os.path.join(self.venv_path, "bin", "python"), "-m", "pip", "install", "-e", "."], check=True)

        # if self.activate:
        #     # TODO: Check if venv is already activated
        #     # TODO: This is Unix/BASH only
        #     os.execlp("source", activate_path)
        # elif self.deactivate:
        #     # TODO: Check if venv was activated
        #     os.execlp("deactivate")


setup(cmdclass={
        'venv': VirtualEnvCommand,
    })
