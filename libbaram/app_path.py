#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from pathlib import Path


if getattr(sys, 'frozen', False):
    APP_PATH = Path(sys.executable).parent.resolve()
else:
    APP_PATH = Path(__file__).parent.parent.resolve()
