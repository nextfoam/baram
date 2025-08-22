#!/usr/bin/env python
# -*- coding: utf-8 -*-

from io import StringIO

import pandas as pd
from PySide6.QtCore import QObject

from baramFlow.openfoam.file_system import FileSystem


def readPostFile(path) -> pd.DataFrame:
    with path.open(mode='r') as f:
        header = None
        line = f.readline()
        while line[0] == '#':
            p = f.tell()
            header = line
            line = f.readline()

        names = header[1:].split()  # read header
        if names[0] != 'Time':
            raise RuntimeError

        if len(names) == 1:
            names.append(path.stem)

        f.seek(p)
        df = pd.read_csv(f, sep=r'\s+', names=names, skiprows=0, engine='python')
        df.set_index('Time', inplace=True)

        return df


class PostFileReader(QObject):
    def __init__(self, name, rname, fileName, extension=None):
        super().__init__()
        self._name = name
        self._path = FileSystem.postProcessingPath(rname) / name
        self._fileName = f'{fileName}{extension}'
        self._pattern = f'{fileName}_*{extension}'
        self._nameLen = len(fileName) + 1
        self._files = {}
        self._currentFilePath = None
        self._currentFile = None
        self._header = None
        self._newLine = ''
        self._cols = None

    def chagedFiles(self):
        self._currentFilePath = None
        changedFiles = []

        dirs = sorted([(d.name, d) for d in self._path.glob('[0-9.]*') if d.name.count('.') < 2],
                      key=lambda x: float(x[0]))
        for dirTime, dirPath in dirs:
            path = dirPath / self._fileName
            if path.is_file() and self._updateFileInfo(path):
                changedFiles.append(self._currentFilePath)
                self._currentFilePath = path

            files = [(f.stem[self._nameLen:], f) for f in dirPath.glob(self._pattern)]
            for time, path in sorted(files, key=lambda x: int(x[0])):
                if self._updateFileInfo(path):
                    changedFiles.append(self._currentFilePath)
                    self._currentFilePath = path

        return changedFiles

    def readDataFrame(self, path):
        with path.open(mode='r') as f:
            header = None
            line = f.readline()
            while line[0] == '#':
                p = f.tell()
                header = line
                line = f.readline()

            names = header[1:].split()  # read header
            if names[0] != 'Time':
                raise RuntimeError
            if len(names) == 1:
                names.append(self._currentFilePath.stem)

            f.seek(p)
            df = pd.read_csv(f, sep=r'\s+', names=names, skiprows=0)
            df.set_index('Time', inplace=True)

            return df

    def readTailDataFrame(self):
        if tail := self._readUpdatedLines():
            stream = StringIO(tail)
            df = pd.read_csv(stream, sep=r'\s+', names=self._header)
            stream.close()
            df.set_index('Time', inplace=True)

            return df

        return None

    def openMonitor(self):
        if self._currentFilePath:
            self._currentFile = open(self._currentFilePath, 'r')

    def closeMonitor(self):
        if self._currentFile:
            self._currentFile.close()
            self._currentFile = None
            self._files[self._currentFilePath] = self._currentFilePath.stat().st_size
            self._currentFilePath = None

    def _updateFileInfo(self, path):
        size = path.stat().st_size
        if path not in self._files or size != self._files[path]:
            self._files[path] = size
            return True

        return False

    def _readUpdatedLines(self):
        lines = self._newLine

        line = self._currentFile.readline()
        if line and line.endswith('\n'):     # complete at least one line including comments
            while line.endswith('\n'):
                lines += line
                if lines[0] == '#':
                    self._header = lines[1:].split()
                    if len(self._header) == 1:
                        self._header.append(self._currentFilePath.stem)
                    lines = ''
                line = self._currentFile.readline()

            self._newLine = line    # Incomplete line is replaced by the new line
            return lines

        self._newLine += line       # New line is still incomplete.
        return ''
