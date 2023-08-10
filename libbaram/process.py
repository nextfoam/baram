#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

from PySide6.QtCore import QObject, Signal


class ProcessError(Exception):
    def __init__(self, returncode):
        self._returncode = returncode

    @property
    def returncode(self):
        return self._returncode


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
        except ProcessLookupError:
            return

    def isCanceled(self):
        return self._canceled

    async def run(self):
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
