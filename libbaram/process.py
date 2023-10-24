#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psutil
import asyncio
import os
import platform
import subprocess

from PySide6.QtCore import QObject, Signal


class ProcessError(Exception):
    def __init__(self, returncode):
        self._returncode = returncode

    @property
    def returncode(self):
        return self._returncode


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
    outputLogged = Signal(str)
    errorLogged = Signal(str)

    def __init__(self, proc=None):
        super().__init__()
        self._proc = proc
        self._canceled = False

    def cancel(self):
        try:
            if self._proc:
                self._proc.terminate()
                self._canceled = True
        except ProcessLookupError:
            return

    def isCanceled(self):
        return self._canceled

    async def run(self):
        self._canceled = False

        outOn = self._proc.stdout is not None
        errOn = self._proc.stderr is not None

        while outOn or errOn:
            if outOn:
                while line := await self._proc.stdout.readline():
                    self.outputLogged.emit(line.decode('UTF-8').rstrip())
                outOn = not self._proc.stdout.at_eof()

            if errOn:
                while line := await self._proc.stderr.readline():
                    self.outputLogged.emit(line.decode('UTF-8').rstrip())
                errOn = not self._proc.stderr.at_eof()

            await asyncio.sleep(1)

        await self._proc.communicate()

        if returncode := self._proc.returncode:
            raise ProcessError(returncode)
