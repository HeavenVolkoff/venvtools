# Internal
import sys
import typing as T
from os import PathLike, name as os_name, environ
from sys import stderr, platform
from venv import EnvBuilder
from types import SimpleNamespace
from pathlib import Path

if sys.version_info < (3, 8):
    # External
    from typing_extensions import TypedDict  # type: ignore
else:
    # Internal
    from typing import TypedDict

# windows detection, covers cpython and ironpython
# link: https://github.com/pypa/pip/blob/476606425a08c66b9c9d326994ff5cf3f770926a/src/pip/_internal/utils/compat.py#L239
WINDOWS = platform.startswith("win") or (platform == "cli" and os_name == "nt")
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


class PopenArgs(TypedDict):
    cwd: str
    args: T.List[str]
    stdin: T.Optional[int]


def _generate_pip_config(config_location: Path, config_values: T.Dict[str, T.Any]) -> None:
    # Internal
    from configparser import ConfigParser

    config = ConfigParser()
    config.read_dict(config_values)

    with config_location.open("w", encoding="utf8") as config_file:
        config.write(config_file)


class ExtendedEnvBuilder(EnvBuilder):
    def __init__(
        self,
        name: str,
        env_name: str,
        project_path: str,
        *,
        rm_main: bool = True,
        verbose: bool = True,
        get_pip: T.Union[bool, str],
        editable: bool,
        project_extras: str = "",
        setup_requires: T.Optional[T.List[str]] = None,
        use_old_resolver: bool = False,
        system_site_packages: bool = False,
    ):
        super().__init__(
            system_site_packages,
            clear=False,
            prompt="[venv: {}]\n".format(env_name),
            symlinks=True,
            with_pip=False,
        )

        self.name = name
        self.rm_main = rm_main and not editable
        self.get_pip = get_pip if isinstance(get_pip, str) else GET_PIP_URL if get_pip else ""
        self.verbose = verbose
        self.editable = editable
        self.project_path = project_path
        self.project_extras = project_extras
        self.setup_requires = setup_requires
        self.use_old_resolver = use_old_resolver

    def announce(self, msg: str) -> None:
        stderr.write(msg)
        stderr.flush()

    def ensure_directories(
        self, env_dir: T.Union[str, bytes, "PathLike[str]", "PathLike[bytes]"]
    ) -> SimpleNamespace:
        context: SimpleNamespace = super().ensure_directories(env_dir)
        # disable default prompt format
        context.prompt = self.prompt

        return context

    def run_script(
        self,
        context: SimpleNamespace,
        name: str,
        *args: T.Any,
        url: T.Optional[str] = None,
        cwd: T.Optional[str] = None,
        message: T.Optional[str] = None,
    ) -> None:
        # Internal
        from subprocess import PIPE, Popen

        data = b""
        proc_kwargs: PopenArgs = {
            "cwd": cwd or context.bin_path,
            "args": [context.env_exe, "-I", "-q"],
            "stdin": None,
        }

        if url:
            if Path(url).is_file():
                proc_kwargs["args"].extend([url, *args])
            else:
                # Internal
                from urllib.request import urlopen

                self.announce("Downloading {}".format(url))

                with urlopen(url) as resp:
                    length = -1
                    while len(data) > length:
                        length = len(data)
                        if length > 12 * 1024 * 1024:
                            raise RuntimeError("Download exceed 12Mb limit")

                        data += resp.read(4096)
                        if self.verbose:
                            stderr.write(".")
                            stderr.flush()
                if self.verbose:
                    stderr.write("\n")
                    stderr.flush()

                proc_kwargs["args"].extend(["-", *args])
                proc_kwargs["stdin"] = PIPE
        else:
            proc_kwargs["args"].extend(["-m", name, *args])

        self.announce("Executing {}".format(message or name))

        with Popen(**proc_kwargs, env=environ) as proc:
            proc.communicate(input=data if data else None, timeout=None)
            if proc.poll() != 0:
                raise RuntimeError(
                    "Failed to execute {} with arguments {}".format(url or name, args)
                )

        self.announce("Done")

    def post_setup(self, context: SimpleNamespace) -> None:
        """
        Set up any packages which need to be pre-installed into the
        environment being created.

        :param context: The information for the environment creation request
                        being processed.
        """
        environ["VIRTUAL_ENV"] = context.env_dir

        # Generate config before using pip so it can load it
        _generate_pip_config(
            Path(context.env_dir) / ("pip.ini" if WINDOWS else "pip.conf"),
            {
                "global": {"require-virtualenv": True},
                "install": {"user": False, "prefix": context.env_dir},
            },
        )

        pip_install_args = ["--upgrade", "--no-cache"]

        if not self.verbose:
            pip_install_args.extend(("--quiet", "--progress-bar", "off"))

        self.announce("Checking if pip is already installed...")

        try:
            # Check if pip is already installed
            self.run_script(context, "pip", "-qqq", "check")
        except RuntimeError:
            if self.get_pip:
                self.run_script(
                    context,
                    "get-pip",
                    *pip_install_args,
                    url=self.get_pip,
                    message="get-pip.py to install pip",
                )
            else:
                self.announce("pip won't be installed")
        else:
            self.announce("pip installed")

        pip_install = ["pip", "install", *pip_install_args]

        if self.use_old_resolver:
            pip_install.append("--use-deprecated=legacy-resolver")

        if self.setup_requires:
            self.run_script(
                context,
                *pip_install,
                *self.setup_requires,
                cwd=self.project_path,
                message="installation of setup requires",
            )

        if self.editable:
            pip_install.append("-e")

        self.run_script(
            context,
            *pip_install,
            ".[{}]".format(self.project_extras) if self.project_extras else ".",
            cwd=self.project_path,
            message="installation of package dependencies",
        )

        if self.rm_main:
            self.run_script(
                context,
                "pip",
                "uninstall",
                "--yes",
                *(() if self.verbose else ("-q",)),
                self.name,
                cwd=self.project_path,
                message="removal of main package",
            )
