#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform

from libbaram.app_path import APP_PATH


_basePath = APP_PATH.joinpath('solvers', 'openfoam', 'lib')
if platform.system() == 'Windows':
    _libExt = '.dll'
elif platform.system() == 'Darwin':
    _libExt = '.dylib'
else:
    _libExt = '.so'


def openfoamLibraryPath(baseName: str) -> str:
    return f'"{str(_basePath.joinpath(baseName).with_suffix(_libExt))}"'
