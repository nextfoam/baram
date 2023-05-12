#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psutil
import asyncio
import os
import platform
import subprocess
import signal

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


async def runExternalScript(program: str, *args, cwd=None, useVenv=True, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL):
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
                                                stdout=stdout,
                                                stderr=stderr)
    return proc


def stopProcess(pid, startTime=None):
    try:
        ps = psutil.Process(pid)
        with ps.oneshot():
            if ps.is_running() and (ps.create_time() == startTime or startTime is None):
                ps.terminate()
    except psutil.NoSuchProcess:
        pass


class Processor(QObject):
    progress = Signal(str)

    def __init__(self, proc=None):
        super().__init__()
        self._proc = proc
        self._canceled = False

    def cancel(self):
        try:
            if self._proc:
                self._proc.terminate()
        except ProcessLookupError:
            return

    def isCanceled(self):
        return self._canceled

    async def run(self, stream):
        while not stream.at_eof() and not self._canceled:
            if line := await stream.readline():
                self.progress.emit(line.decode('UTF-8'))
            else:
                await asyncio.sleep(1)

        await self._proc.communicate()
        self._proc = None


class ProcessCanceledException(Exception):
    pass
