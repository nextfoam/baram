#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform
import sys

from pathlib import Path


if getattr(sys, 'frozen', False):
    if platform.system() == 'Darwin':
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        APP_PATH = Path(sys._MEIPASS)  # ex. "/Applications/BaramFlow.app/Contents/Frameworks"
    else:
        APP_PATH = Path(sys.executable).parent.resolve()
else:
    APP_PATH = Path(__file__).parent.parent.resolve()
