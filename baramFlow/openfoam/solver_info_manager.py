#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import re
from typing import Final, TextIO, Optional
from io import StringIO
from pathlib import Path
from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QTimer, QObject, QThread, Signal

from baramFlow.case_manager import CaseManager


# One solverInfo file per "Region" is updated by solver during calculation.
# By the way, there can be a region where the solverInfo is not updated.
# It is a case when there is no field to calculate since calculation is disabled in Advanced numerical condition.
# (Typically in solid region when energy equation is configured not to be solved)
# When identifying these changing files, once a file in a region is detected as changing, charting can start.
# Yet we need to wait for a while until the writing is settled.
CHANGING_FILE_CHEKING_THRESHOLD_COUNT: Final[int] = 2


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

mrRegexPattern = r'(?P<rname>[^/\\]+)[/\\]solverInfo_\d+[/\\](?P<time>[0-9]+(?:\.[0-9]+)?)[/\\]solverInfo(?:_(?P<dup>[0-9]+(?:\.[0-9]+)?))?\.dat'
srRegexPattern = r'[/\\]solverInfo_\d+[/\\](?P<time>[0-9]+(?:\.[0-9]+)?)[/\\]solverInfo(?:_(?P<dup>[0-9]+(?:\.[0-9]+)?))?\.dat'


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class _SolverInfo:
    rname: str
    time: float
    dup: str
    size: int
    path: Path
    f: Optional[TextIO]


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


def readOutFile(f: TextIO):
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


def mergeDataFrames(data: [pd.DataFrame]):
    merged = None
    for df in data:
        if df is None:
            continue
        
        if merged is None:
            merged = df
        else:
            left_on = {'Time', *(merged.columns.values.tolist())}
            right_on = {'Time', *(df.columns.values.tolist())}
            on = list(left_on.intersection(right_on))

            # "merge" rather than "concat" should be used because of multi-region cases
            merged = pd.merge(merged, df, how='outer', on=on)
            merged = merged.sort_values(by='Time')

    return merged


def updateData(target, source):
    if target is None:
        return source
    else:
        # Drop obsoleted rows.
        # Dataframes should be kept PER REGION because of this dropping.
        # If dataframes of regions are merged, updated data in other regions can be lost.
        time = source.first_valid_index()
        filtered = target[target.index < time]
        return mergeDataFrames([filtered, source])


class Worker(QObject):
    start = Signal()
    stop = Signal()
    updateResiduals = Signal()
    residualsUpdated = Signal(pd.DataFrame)
    flushed = Signal()

    def __init__(self, casePath: Path, regions: [str]):
        super().__init__()

        self.mrGlobPattern = casePath / 'postProcessing' / '*' / 'solverInfo_*' / '*' / 'solverInfo*.dat'
        self.srGlobPattern = casePath / 'postProcessing' / 'solverInfo_*' / '*' / 'solverInfo*.dat'

        self.regions = regions

        self.changingFiles = None
        self.data = None

        self.collectionReady = 0

        self.infoFiles = None

        self.timer = None
        self.running = False

        self.start.connect(self.startRun, type=Qt.ConnectionType.QueuedConnection)
        self.stop.connect(self.stopRun, type=Qt.ConnectionType.QueuedConnection)

    def startRun(self):
        if self.running:
            return

        self.running = CaseManager().isRunning()

        self.collectionReady = 0

        self.changingFiles = {r: None for r in self.regions}
        self.data = {r: None for r in self.regions}

        if self.running:
            # Get current snapshot of info files
            self.infoFiles = self.getInfoFiles()

            self.timer = QTimer()
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.process)
            self.timer.start()
        else:
            self.infoFiles = {}
            self.process()
            self.stopRun()
            self.flushed.emit()

    def stopRun(self):
        if self.running:
            self.timer.stop()

        self.process()

        for s in self.changingFiles.values():
            if s is not None and s.f is not None:  # "s" or "s.f" could remain "None" if the solver stops by error as soon as it starts
                s.f.close()
        QThread.currentThread().quit()
        self.running = False

    def process(self):
        updatedFiles = self.getUpdatedFiles(self.infoFiles)
        for p, s in updatedFiles.items():
            if p in self.infoFiles:
                self.infoFiles[p].size = s.size
            else:
                self.infoFiles[p] = s

            if self.changingFiles[s.rname] is None or self.infoFiles[p].time > self.changingFiles[s.rname].time:
                self.changingFiles[s.rname] = self.infoFiles[p]

        if self.collectionReady < CHANGING_FILE_CHEKING_THRESHOLD_COUNT:
            collectionReady = any(self.changingFiles.values())
            if not collectionReady:
                return
            else:
                self.collectionReady += 1
                if self.collectionReady < CHANGING_FILE_CHEKING_THRESHOLD_COUNT:
                    return

                hasUpdate = False
                for s in self.infoFiles.values():
                    if s not in self.changingFiles.values():  # not-changing files
                        df = self._getDataFrame(s.rname, s.path)
                        if df is not None:
                            self.data[s.rname] = updateData(self.data[s.rname], df)

                for s in self.changingFiles.values():
                    if s is None:
                        continue

                    s.f = open(s.path, 'r')
                    updated, df = self._updateDataFromFile(self.data[s.rname], s.rname, s.f)
                    if updated:
                        self.data[s.rname] = updateData(self.data[s.rname], df)
                        hasUpdate = True

                if hasUpdate:
                    self.residualsUpdated.emit(mergeDataFrames(self.data.values()))

                return

        # regular update routine
        hasUpdate = False
        for s in updatedFiles.values():
            updated, df = self._updateDataFromFile(self.data[s.rname], s.rname, self.infoFiles[s.path].f)
            if updated:
                self.data[s.rname] = df
                hasUpdate = True

        if hasUpdate:
            self.residualsUpdated.emit(mergeDataFrames(self.data.values()))

    def getUpdatedFiles(self, current: {Path: _SolverInfo}) -> {Path: _SolverInfo}:
        infoFiles = self.getInfoFiles()

        updatedFiles = {}

        for p, s in infoFiles.items():
            if (p not in current) or (s.size != current[p].size):
                updatedFiles[p] = s

        return updatedFiles

    def _getInfoFilesMultiRegion(self) -> {Path: _SolverInfo}:
        mrFiles = [((p := Path(pstr)), p.stat().st_size) for pstr in glob.glob(str(self.mrGlobPattern))]
        infoFiles = {}
        for path, size in mrFiles:
            m = re.search(mrRegexPattern, str(path))
            if m.group('rname') not in self.regions:
                continue
            infoFiles[path] = _SolverInfo(m.group('rname'), float(m.group('time')), m.group('dup'), size, path, None)
        return infoFiles

    def _getInfoFilesSingleRegion(self) -> {Path: _SolverInfo}:
        srFiles = [((p := Path(pstr)), p.stat().st_size) for pstr in glob.glob(str(self.srGlobPattern))]
        infoFiles = {}
        for path, size in srFiles:
            m = re.search(srRegexPattern, str(path))
            infoFiles[path] = _SolverInfo('', float(m.group('time')), m.group('dup'), size, path, None)
        return infoFiles

    def getInfoFiles(self) -> {Path: _SolverInfo}:
        if len(self.regions) > 1:
            infoFiles = self._getInfoFilesMultiRegion()
        else:
            infoFiles = self._getInfoFilesSingleRegion()

        # Drop obsoleted info file, which has newer info file in the same directory
        newerFiles = [p.parent for p, s in infoFiles.items() if s.dup is not None]
        infoFiles = {p: s for p, s in infoFiles.items() if s.dup is not None or s.path.parent not in newerFiles}

        infoFiles = dict(sorted(infoFiles.items(), key=lambda x: (x[1].rname, x[1].time)))

        return infoFiles

    def update(self):
        self.residualsUpdated.emit(mergeDataFrames(self.data.values()))

    def _updateDataFromFile(self, target: pd.DataFrame, rname: str, f: TextIO) -> (bool, pd.DataFrame):
        lines, names = readOutFile(f)
        if not lines:
            return False, target

        names, columns = self._getResidualHeader(names, rname)

        stream = StringIO(lines)
        df = pd.read_csv(stream, sep=r'\s+', names=names, dtype={'Time': np.float64})[columns]
        stream.close()

        df.set_index('Time', inplace=True)

        return True, updateData(target, df)

    def _getDataFrame(self, rname, path) -> Optional[pd.DataFrame]:
        with path.open(mode='r') as f:
            f.readline()  # skip '# Solver information' comment
            names = f.readline().split()  # read header
            if len(names) == 0:
                return None

            names.pop(0)  # remove '#' from the list
            if names[0] != 'Time':
                raise RuntimeError

            names, columns = self._getResidualHeader(names, rname)

            df = pd.read_csv(f, sep=r'\s+', names=names, dtype={'Time': np.float64}, skiprows=0)[columns]
            df.set_index('Time', inplace=True)
            return df

    def _getResidualHeader(self, names: [str], rname: str):
        header = names.copy()
        columns = [names[0]]     # Time
        for i in range(1, len(names)):
            if names[i].endswith('_initial'):
                header[i] = names[i][:-8]
                columns.append(header[i])

        if rname != '':
            header = [k if k == 'Time' else rname + ':' + k for k in header]
            columns = [k if k == 'Time' else rname + ':' + k for k in columns]

        return header, columns


class SolverInfoManager(QObject):
    residualsUpdated = Signal(pd.DataFrame)
    flushed = Signal()

    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

    def startCollecting(self, casePath: Path, regions: [str]):
        if self.thread is not None:
            self.stopCollecting()

        if not casePath.is_absolute():
            raise AssertionError

        self.thread = QThread()
        self.worker = Worker(casePath, regions)

        self.worker.moveToThread(self.thread)

        self.worker.residualsUpdated.connect(self.residualsUpdated, type=Qt.ConnectionType.QueuedConnection)
        self.worker.flushed.connect(self.flushed, type=Qt.ConnectionType.QueuedConnection)

        self.thread.start()

        self.worker.start.emit()

    def stopCollecting(self):
        if self.thread is None:
            return

        self.worker.stop.emit()
        self.thread.wait(1000)  # usually 1ms is sufficient, yet delay over 500ms was seen once

        self.worker = None
        self.thread = None

    def updateResiduals(self):
        if self.thread is None:
            raise FileNotFoundError

        self.worker.updateResiduals.emit()
