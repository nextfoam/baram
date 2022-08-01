#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import re
import typing
from io import StringIO
from pathlib import Path
from dataclasses import dataclass
from threading import Lock
import logging

import numpy as np
import pandas as pd
from PySide6.QtCore import QTimer, QObject, QThread, Signal


# "solverInfo.dat" sample
#   It is tab separated yet has spaces in it.
"""
# Solver information
# Time          	U_solver        	Ux_initial      	Ux_final        	Ux_iters        	Uy_initial      	Uy_final        	Uy_iters        	Uz_initial      	Uz_final        	Uz_iters        	U_converged     
0.0120482       	DILUPBiCGStab	1.00000000e+00	8.58724200e-08	1	1.00000000e+00	5.78842110e-14	1	1.00000000e+00	6.57355850e-14	1	false
0.0265769       	DILUPBiCGStab	3.66757700e-01	2.17151110e-13	1	9.06273050e-01	3.18900850e-13	1	3.76387760e-01	3.48509970e-13	1	false
0.0439595       	DILUPBiCGStab	2.31957720e-02	2.67950170e-08	1	5.38653860e-01	3.35496420e-13	1	3.79282860e-02	5.53125350e-08	1	false
...
"""
_mutex = Lock()

mrRegexPattern = r'(?P<region>[^/\\]+)[/\\]solverInfo_\d+[/\\](?P<time>[0-9]+(?:\.[0-9]+)?)[/\\]solverInfo(?:_(?P<dup>[0-9]+(?:\.[0-9]+)?))?\.dat'
srRegexPattern = r'[/\\]solverInfo_\d+[/\\](?P<time>[0-9]+(?:\.[0-9]+)?)[/\\]solverInfo(?:_(?P<dup>[0-9]+(?:\.[0-9]+)?))?\.dat'


logger = logging.getLogger(__name__)
formatter = logging.Formatter("[%(name)s] %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@dataclass
class _SolverInfo:
    region: str
    time: float
    dup: str
    size: int
    path: Path
    f: typing.TextIO


def readCompleteLineOnly(f):
    line = f.readline()
    if line.endswith('\n'):
        if hasattr(f, 'incompleteLine'):
            line = f.incompleteLine + line
            f.incompleteLine = ''
        return line
    else:
        if hasattr(f, 'incompleteLine'):
            f.incompleteLine += line
        else:
            f.incompleteLine = line
        return ''


def readOutFile(f: typing.TextIO):
    lines = ''

    while line := readCompleteLineOnly(f):
        if not hasattr(f, 'residualHeader'):  # Initial State
            if not line.startswith('# Solver information'):
                raise RuntimeError
            f.residualHeader = None
        elif not f.residualHeader:  # Waiting residual header
            names = line.split()
            names.pop(0)  # remove '#' from the list
            if names[0] != 'Time':
                raise RuntimeError
            f.residualHeader = names
        else:  # Parse residuals
            lines += line

    if hasattr(f, 'residualHeader'):
        return lines, f.residualHeader
    else:
        return lines, None


def updateData(target, source: str, names: [str]):
    stream = StringIO(source)
    df = pd.read_csv(stream, sep=r'\s+', names=names, dtype={'Time': np.float64})
    stream.close()

    df.set_index('Time', inplace=True)

    if target is not None:
        left_on = {'Time', *(target.columns.values.tolist())}
        right_on = {'Time', *(df.columns.values.tolist())}
        on = list(left_on.intersection(right_on))
        time = df.first_valid_index()
        filtered = target[target.index < time]  # Drop obsoleted rows
        return pd.merge(filtered, df, how='outer', on=on)
    else:
        return df


class Worker(QObject):
    start = Signal(Path)
    stop = Signal()
    update = Signal()
    updated = Signal(pd.DataFrame)

    def __init__(self):
        super().__init__()

        self.data = {}

        self.mrGlobPattern = None
        self.srGlobPattern = None

        self.infoFiles = None

        self.timerVar = None
        self.running = False

        self.start.connect(self.startRun)
        self.stop.connect(self.stopRun)

    def startRun(self, path: Path):
        if self.running:
            return

        print('startRun'+str(path))
        self.running = True

        self.mrGlobPattern = path / 'postProcessing' / '*' / 'solverInfo_*' / '*' / 'solverInfo*.dat'
        self.srGlobPattern = path / 'postProcessing' / 'solverInfo_*' / '*' / 'solverInfo*.dat'

        infoFiles = self.getInfoFiles()
        for p, s in infoFiles.items():
            s.f = open(s.path, 'r')
            lines, names = readOutFile(s.f)
            if not lines:
                continue

            if s.region != '':
                names = [k if k == 'Time' else s.region + ':' + k for k in names]

            if s.region in self.data:
                self.data[s.region] = updateData(self.data[s.region], lines, names)
            else:
                self.data[s.region] = updateData(None, lines, names)

        self.infoFiles = infoFiles

        self.timerVar = QTimer()
        self.timerVar.setInterval(500)
        self.timerVar.timeout.connect(self.process)
        self.timerVar.start()

        self.updated.emit(list(self.data.values()))

    def stopRun(self):
        self.timerVar.stop()
        self.running = False

    def process(self):
        print('Timeout')
        infoFiles = self.getUpdatedFiles(self.infoFiles)
        for p, s in infoFiles.items():
            # close all the other files in the same region
            for p1, s1 in self.infoFiles.items():
                if p1 != p and s1.region == s.region and s1.f is not None:
                    s1.f.close()

            print('updated SolverInfo: '+str(p))

            if p in self.infoFiles:
                self.infoFiles[p].size = s.size
            else:
                self.infoFiles[p] = s
                s.f = open(s.path, 'r')

            lines, names = readOutFile(self.infoFiles[p].f)
            if not lines:
                continue

            if s.region != '':
                names = [k if k == 'Time' else s.region + ':' + k for k in names]

            if s.region in self.data:
                self.data[s.region] = updateData(self.data[s.region], lines, names)
            else:
                self.data[s.region] = updateData(None, lines, names)

        self.updated.emit(list(self.data.values()))

    def getUpdatedFiles(self, current: {Path: _SolverInfo}) -> {Path: _SolverInfo}:
        infoFiles = self.getInfoFiles()

        updatedFiles = {}

        for p, s in infoFiles.items():
            if (p not in current) or (s.size != current[p].size):
                updatedFiles[p] = s

        return updatedFiles

    def getInfoFiles(self) -> {Path: _SolverInfo}:
        mrFiles = [((p := Path(pstr)), p.stat().st_size) for pstr in glob.glob(str(self.mrGlobPattern))]
        srFiles = [((p := Path(pstr)), p.stat().st_size) for pstr in glob.glob(str(self.srGlobPattern))]

        infoFiles = {}

        for path, size in mrFiles:
            m = re.search(mrRegexPattern, str(path))
            infoFiles[path] = _SolverInfo(m.group('region'), float(m.group('time')), m.group('dup'), size, path, None)

        for path, size in srFiles:
            m = re.search(srRegexPattern, str(path))
            infoFiles[path] = _SolverInfo('', float(m.group('time')), m.group('dup'), size, path, None)

        # Drop obsoleted info file, which has newer info file in the same directory
        newerFiles = [p for p, s in infoFiles.items() if s.dup is not None]
        infoFiles = {p: s for p, s in infoFiles.items() if s.dup is not None or s.path not in newerFiles}

        infoFiles = dict(sorted(infoFiles.items(), key=lambda x: (x[1].region, x[1].time)))

        return infoFiles

    def update(self):
        self.updated.emit(list(self.data.values()))


class SolverInfoManager(QObject):
    updated = Signal(pd.DataFrame)

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(SolverInfoManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, path: Path):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        if not path.is_absolute():
            raise AssertionError

        super().__init__()

        self.path = path

        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)

        self.worker.updated.connect(self.updated)

        self.thread.start()

    def startCollecting(self):
        self.worker.start.emit(self.path)

    def stopCollecting(self):
        self.worker.stop.emit()

    def update(self):
        self.worker.update.emit()


def getSolverInfoManager(path: Path):
    return SolverInfoManager(path)
