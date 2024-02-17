#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
import psutil

from libbaram import process


class SolverStatus(Enum):
    NONE = 0
    WAITING = auto()
    RUNNING = auto()
    ENDED = auto()


class RunType(Enum):
    PROCESS = auto()
    JOB = auto()


class SolverProcess:
    def __init__(self, pid, startTime):
        self._pid = pid
        self._startTime = startTime

    @property
    def pid(self):
        return self._pid

    @property
    def startTime(self):
        return self._startTime

    def isRunning(self):
        return process.isRunning(self._pid, self._startTime)

    def kill(self):
        if not self.isRunning():
            return

        try:
            ps = psutil.Process(self._pid)
            with ps.oneshot():
                if ps.is_running() and ps.create_time() == self._startTime:
                    ps.terminate()
        except psutil.NoSuchProcess:
            pass


