#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psutil
import asyncio
import os
import platform
import subprocess

from PySide6.QtCore import QObject, Signal


def isRunning(pid, startTime):
    if pid and startTime:
        try:
            ps = psutil.Process(pid)
            if ps.create_time() == startTime:
                return True
        except psutil.NoSuchProcess:
            return False

    return False


async def runExternalScript(program: str, *args, cwd=None, useVenv=True, stderr=None):
    ENV = os.environ.copy()
    if not useVenv:
        excluding = [os.path.join('venv', 'bin'), os.path.join('venv', 'Lib'), os.path.join('venv', 'Scripts')]
        ENV['PATH'] = os.pathsep.join([path for path in ENV['PATH'].split(os.pathsep) if not any([pattern in path for pattern in excluding])])

    creationflags = 0
    startupinfo = None

    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESHOWWINDOW,
            wShowWindow=subprocess.SW_HIDE
        )

    proc = await asyncio.create_subprocess_exec(program, *args,
                                                env=ENV, cwd=cwd,
                                                creationflags=creationflags,
                                                startupinfo=startupinfo,
                                                stderr=stderr)
    return proc


class Processor(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()
        self._proc = None

    def cancel(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None


class ProcessCanceledException(Exception):
    pass
