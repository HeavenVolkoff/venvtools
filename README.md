# venvtools

A simple setuptools command to help with virtualenv

### Motivation

The objective of this utility is to provide means for easy creation of a virtual
environment for local packages using python's standard venv module and to integrate
with setuptools distribution model for seamless resolution and installation of
dependencies.

### How to use

Inside your package root folder execute the following to create the venv and install
your package dependencies inside it:
```shell
python ./setup.py venv
```
or (if your `setup.py` is executable)
```shell
./setup.py venv
```

> Currently updating dependencies inside the venv is not working correctly.
> It's recommended to recreate the venv to archive it.
>
> (This will be fixed in a posterior version)
```shell
./setup.py venv --rm && ./setup.py venv
```

#### Options
```
--env-name (-n)         Virtual environment name.
                        (DEFAULT: Project name)
--get-pip               Virtual env get-pip.py URL.
                        (DEFAULT: https://bootstrap.pypa.io/get-pip.py)
--extras (-e)           Comma separated list of extras to be installed.
--system-site-packages  Make the system (global) site-packages dir available to the
                        created environment.
--rm                    Remove virtual environment.
--editable              Install package to venv as editable.
--location (-l)         Retrieve virtual environment location.
```

### License

See [LICENSE](./LICENSE)

### COPYRIGHT

    Copyright (c) 2018-2020 Vítor Augusto da Silva Vasconcellos. All rights reserved.
