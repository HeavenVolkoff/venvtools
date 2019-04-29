# Internal
import typing as T
from os import path
from venv import EnvBuilder
from types import SimpleNamespace


class ExtendedEnvBuilder(EnvBuilder):
    def __init__(
        self,
        name,
        env_name,
        project_path,
        *args,
        rm_main: bool = True,
        verbose: bool = True,
        get_pip: T.Union[bool, str],
        editable: bool,
        project_extras: str = "",
        setup_requires: T.List[str] = None,
        **kwargs,
    ):
        super().__init__(
            *args,
            clear=False,
            prompt="[venv: {}]\n".format(env_name),
            symlinks=True,
            with_pip=False,
            **kwargs,
        )

        self.name = name
        self.rm_main = rm_main or not editable
        self.get_pip = get_pip
        self.verbose = verbose
        self.editable = editable
        self.project_path = project_path
        self.project_extras = project_extras
        self.setup_requires = setup_requires

    def announce(self, msg):
        from sys import stderr

        stderr.write(msg)
        stderr.flush()

    def ensure_directories(self, *args, **kwargs):
        context = super().ensure_directories(*args, **kwargs)
        # disable default prompt format
        context.prompt = self.prompt

        return context

    def run_script(
        self,
        context: SimpleNamespace,
        name: str,
        *args,
        url: str = None,
        cwd: str = None,
        message: str = None,
    ):
        from sys import stderr
        from contextlib import ExitStack
        from subprocess import PIPE, Popen

        with ExitStack() as stack:
            data = None
            proc_kwargs = {"cwd": cwd or context.bin_path, "args": [context.env_exe, "-q"]}
            if url:
                if path.isfile(url):
                    proc_kwargs["args"].extend([url, *args])
                else:
                    from urllib.request import urlopen

                    self.announce("Downloading {}".format(url))

                    data = b""
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

            proc = stack.enter_context(Popen(**proc_kwargs))
            proc.communicate(input=data, timeout=None)
            if proc.poll() != 0:
                raise RuntimeError(
                    "Failed to execute {} with arguments {}".format(url or name, args)
                )

        self.announce("Done")

    def post_setup(self, context: SimpleNamespace):
        """
        Set up any packages which need to be pre-installed into the
        environment being created.

        :param context: The information for the environment creation request
                        being processed.
        """
        from os import environ

        environ["VIRTUAL_ENV"] = context.env_dir

        try:
            # Check if pip is already installed
            self.run_script(context, "pip", "-qqq", "check")
        except RuntimeError:
            self.run_script(
                context, "get-pip", *(() if self.verbose else ("-q",)), url=self.get_pip
            )

        pip_install = ["pip", "install", "--no-cache", "-U"]
        if not self.verbose:
            pip_install.extend(("--progress-bar", "off", "-q"))

        if self.setup_requires:
            self.run_script(
                context,
                *pip_install,
                *self.setup_requires,
                cwd=self.project_path,
                message="installation of setup requires",
            )

        if self.editable:
            pip_install.extend(("-e",))

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
