#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from PySide6.QtCore import QCoreApplication


OPENFOAM_PATH_PART_PATTERN = r'[A-Za-z0-9_.]+'

pattern = re.compile(OPENFOAM_PATH_PART_PATTERN)


def getOpenFOAMPathError(path: Path):
    parts = list(path.parts)
    if path.root == '\\':                   # Windows path
        parts[0] = ''                                   # ignore drive name or network root
        if not path.drive.endswith(':'):    # Windows network path
            parts = path.drive.split('\\') + parts      # add split network root to parts for checking
    elif path.root == '/':                  # POSIX absolute path
        parts[0] = ''                                   # ignore first slash

    for p in parts:
        if p != '' and not pattern.fullmatch(p):
            return QCoreApplication.translate('OpenFOAMPath', 'Invalid path. "{0}" contains invalid characters.').format(p)

    return None
