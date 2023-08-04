#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

from PySide6.QtCore import QObject, Signal


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
        outOver = self._proc.stdout is None
        errOver = self._proc.stderr is None

        while not (outOver and errOver):
            if not outOver:
                while line := await self._proc.stdout.readline():
                    self.outputLogged.emit(line.decode('UTF-8').rstrip())
                outOver = self._proc.stdout.at_eof()

            if not errOver:
                while line := await self._proc.stderr.readline():
                    self.outputLogged.emit(line.decode('UTF-8').rstrip())
                errOver = self._proc.stderr.at_eof()

            await asyncio.sleep(1)

        await self._proc.communicate()

        return self._proc.returncode
