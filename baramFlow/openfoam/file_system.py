#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from typing import Optional
from pathlib import Path
import re

import asyncio

from libbaram import utils
from libbaram.openfoam.constants import Directory, CASE_DIRECTORY_NAME, FOAM_FILE_NAME
from libbaram.openfoam.polymesh import isPolyMesh

from resources import resource


class FileLoadingError(Exception):
    pass


def clearDirectory(directory, filesToKeep, fileToKeep=None):
    for file in directory.glob('*'):
        if file.name not in filesToKeep and file.name != fileToKeep:
            remove(file)


def remove(file):
    if file.is_dir():
        utils.rmtree(file)
    else:
        file.unlink()


class FileSystem:
    _casePath: Optional[Path] = None
    _constantPath = None
    _boundaryConditionsPath = None
    _systemPath = None
    _postProcessingPath = None

    _caseFilesToKeep = [
        Directory.CONSTANT_DIRECTORY_NAME,
        Directory.SYSTEM_DIRECTORY_NAME,
        FOAM_FILE_NAME,
        # Directory.BOUNDARY_CONDITIONS_DIRECTORY_NAME
    ]
    _constantFilesToKeep = [Directory.POLY_MESH_DIRECTORY_NAME, Directory.REGION_PROPERTIES_FILE_NAME]

    @classmethod
    def createCase(cls, path):
        if path.exists():
            utils.rmtree(path)

        shutil.copytree(resource.file('openfoam/case'), path)

        cls.makeDir(path, Directory.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        cls.makeDir(path, Directory.CONSTANT_DIRECTORY_NAME)

    @classmethod
    def linkLivePolyMeshTo(cls, livePath, targetPath, regions, processorOnly = False):
        # To check folders is better than to get "NP" from the configuration
        # to avoid possible mismatch between number of folders and "NP" configuration in the future
        np = len(list(livePath.glob('processor[0-9]*')))
        processorFolders = [f'processor{i}' for i in range(0, np)]
        if not processorOnly:
            processorFolders.insert(0, '')  # Reconstructed folder

        for processor in processorFolders:
            liveConstant = livePath / processor / Directory.CONSTANT_DIRECTORY_NAME
            liveSystem   = livePath / processor / Directory.SYSTEM_DIRECTORY_NAME  # noqa: E221

            if not liveConstant.is_dir():
                continue

            batchConstant = targetPath / processor / Directory.CONSTANT_DIRECTORY_NAME
            batchSystem   = targetPath / processor / Directory.SYSTEM_DIRECTORY_NAME  # noqa: E221

            if len(regions) > 1:
                if processor == '':  # RegionProperties file is not copied for processor folders
                    source = liveConstant  / Directory.REGION_PROPERTIES_FILE_NAME  # noqa: E221
                    target = batchConstant / Directory.REGION_PROPERTIES_FILE_NAME
                    shutil.copyfile(source, target)

                for rname in regions:
                    target = liveConstant  / rname / Directory.POLY_MESH_DIRECTORY_NAME  # noqa: E221
                    source = batchConstant / rname / Directory.POLY_MESH_DIRECTORY_NAME
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)  # "walk_up" option for pathlib.Path.relative_to() is not available in python 3.9
                    if processor == '':  # decomposePar file should not be copied for processor folders
                        target = liveSystem  / rname / 'decomposeParDict'  # noqa: E221
                        source = batchSystem / rname / 'decomposeParDict'
                        source.parent.mkdir(parents=True, exist_ok=True)
                        source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=False)  # "walk_up" option for pathlib.Path.relative_to() is not available in python 3.9
            else:
                target = liveConstant  / Directory.POLY_MESH_DIRECTORY_NAME  # noqa: E221
                source = batchConstant / Directory.POLY_MESH_DIRECTORY_NAME
                source.parent.mkdir(parents=True, exist_ok=True)
                source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=True)  # "walk_up" option for pathlib.Path.relative_to() is not available in python 3.9
                if processor == '':  # decomposePar file should not be copied for processor folders
                    target = liveSystem  / 'decomposeParDict'  # noqa: E221
                    source = batchSystem / 'decomposeParDict'
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.symlink_to(os.path.relpath(target, source.parent), target_is_directory=False)  # "walk_up" option for pathlib.Path.relative_to() is not available in python 3.9

    @classmethod
    def createBatchCase(cls, livePath, path, regions):
        cls.createCase(path)

        cls.linkLivePolyMeshTo(livePath, path, regions)

        with open(path / FOAM_FILE_NAME, 'a'):
            pass

    @classmethod
    def initRegionDirs(cls, rname):
        cls.makeDir(cls._boundaryConditionsPath, rname)
        cls.makeDir(cls._constantPath, rname)
        cls.makeDir(cls._systemPath, rname)

    @classmethod
    def caseRoot(cls):
        return cls._casePath

    @classmethod
    def setCaseRoot(cls, path):
        cls._casePath = path
        cls._constantPath = cls._casePath / Directory.CONSTANT_DIRECTORY_NAME
        cls._boundaryConditionsPath = cls._casePath / Directory.BOUNDARY_CONDITIONS_DIRECTORY_NAME
        cls._systemPath = cls._casePath / Directory.SYSTEM_DIRECTORY_NAME
        cls._postProcessingPath = cls._casePath / Directory.POST_PROCESSING_DIRECTORY_NAME

    @classmethod
    def constantPath(cls, rname=''):
        return cls._constantPath / rname

    @classmethod
    def boundaryConditionsPath(cls, rname=''):
        return cls._boundaryConditionsPath / rname

    @classmethod
    def systemPath(cls, rname=''):
        return cls._systemPath / rname

    @classmethod
    def latestTime(cls, parent: Optional[Path] = None) -> str:
        times = cls.times(parent)
        if len(times) == 0:
            return '0'

        return times[-1]

    @classmethod
    def times(cls, parent: Optional[Path] = None) -> list[str]:
        if parent is None:
            parent = cls.processorPath(0)
            if parent is None:
                parent = cls._casePath

        times = []
        for f in parent.iterdir():
            if not f.is_dir():
                continue

            if re.fullmatch(r'^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$', f.name):
                times.append(f.name)

        return sorted(times, key=lambda x: float(x))

    @classmethod
    def fieldExists(cls, time: str, fieldStr: str) -> bool:
        parent = cls.processorPath(0)
        if parent is None:
            parent = cls._casePath

        path = parent / time / fieldStr
        if path.is_file():
            return True

        # in case it is multi-region case
        for path in parent.joinpath(time).glob(f'*/{fieldStr}'):
            if path.is_file():
                return True

        return False

    @classmethod
    def polyMeshPath(cls, rname=''):
        return cls.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME

    @classmethod
    def boundaryFilePath(cls, rname):
        return cls.polyMeshPath(rname) / 'boundary'

    @classmethod
    def cellZonesFilePath(cls, rname):
        return cls.polyMeshPath(rname) / 'cellZones'

    @classmethod
    def boundaryDataPath(cls, rname):
        return cls.constantPath(rname) / rname / Directory.BOUNDARY_DATA_DIRECTORY_NAME

    @classmethod
    def postProcessingPath(cls, rname=''):
        return cls._postProcessingPath / rname

    @classmethod
    def foamFilePath(cls):
        # ToDo: For compatibility. Remove this code block after 20251231
        # Migration from previous name of "baram.foam"
        # Begin
        path = cls._casePath / FOAM_FILE_NAME
        if cls._casePath.is_dir() and not path.is_file():
            with open(path, 'a'):
                pass
        # End

        return cls._casePath / FOAM_FILE_NAME

    @classmethod
    def processorPath(cls, no):
        path = (cls._casePath / f'processor{no}')

        return path if path.is_dir() else None

    @classmethod
    def makeDir(cls, parent: Path, directory) -> Path:
        path = parent / directory
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def hasPolyMesh(cls):
        return (isPolyMesh(cls.polyMeshPath())
                or cls.constantPath().joinpath(Directory.REGION_PROPERTIES_FILE_NAME).is_file())

    @classmethod
    def processorFolders(cls):
        return list(cls._casePath.glob('processor[0-9]*'))

    @classmethod
    def numberOfProcessorFolders(cls):
        return len(cls.processorFolders())

    @classmethod
    def hasCalculationResults(cls):
        return cls._postProcessingPath.exists()

    @classmethod
    async def copyFileToCase(cls, file, name):
        await asyncio.to_thread(shutil.copyfile, file, cls._casePath / name)

    @classmethod
    async def removeFile(cls, file):
        path = cls._casePath / file
        path.unlink()

    @classmethod
    def saveAs(cls, sourcePath, projectPath, regions):
        def copyDirectory(srcPath, destPath, directory):
            shutil.copytree(srcPath / directory, destPath / directory, copy_function=shutil.copyfile)

        def copyFile(srcPath, destPath, file):
            shutil.copyfile(srcPath / file, destPath / file)

        sourceCaseRoot = sourcePath / CASE_DIRECTORY_NAME
        sourceConstantPath = sourceCaseRoot / Directory.CONSTANT_DIRECTORY_NAME
        sourceSystemPath = sourceCaseRoot / Directory.SYSTEM_DIRECTORY_NAME

        targetCaseRoot = projectPath / CASE_DIRECTORY_NAME
        targetConstantPath = targetCaseRoot / Directory.CONSTANT_DIRECTORY_NAME
        targetSystemPath = targetCaseRoot / Directory.SYSTEM_DIRECTORY_NAME

        cls.createCase(targetCaseRoot)
        if sourceConstantPath.is_dir():
            processorFolders = cls.processorFolders()

            if len(regions) > 1:
                copyFile(sourceConstantPath, targetConstantPath, Directory.REGION_PROPERTIES_FILE_NAME)

                for rname in regions:
                    copyDirectory(sourceConstantPath, targetConstantPath, rname)
                    if len(processorFolders):
                        copyFile(sourceSystemPath / rname, cls.makeDir(targetSystemPath, rname), 'decomposeParDict')

                    for processorPath in processorFolders:
                        destProcessorPath = cls.makeDir(targetCaseRoot, processorPath.name)
                        copyDirectory(processorPath / Directory.CONSTANT_DIRECTORY_NAME,
                                      cls.makeDir(destProcessorPath, Directory.CONSTANT_DIRECTORY_NAME),
                                      rname)
            else:
                copyDirectory(sourceConstantPath, targetConstantPath, Directory.POLY_MESH_DIRECTORY_NAME)
                for processorPath in processorFolders:
                    destProcessorPath = cls.makeDir(targetCaseRoot, processorPath.name)
                    copyDirectory(processorPath / Directory.CONSTANT_DIRECTORY_NAME,
                                  cls.makeDir(destProcessorPath, Directory.CONSTANT_DIRECTORY_NAME),
                                  Directory.POLY_MESH_DIRECTORY_NAME)

            if len(processorFolders):
                copyFile(sourceSystemPath, targetCaseRoot / Directory.SYSTEM_DIRECTORY_NAME, 'decomposeParDict')

            with open(targetCaseRoot / FOAM_FILE_NAME, 'a'):
                pass

    @classmethod
    def deleteCalculationResults(cls, time: str = None):
        folders = [cls._postProcessingPath]

        for parent in [cls._casePath, *cls.processorFolders()]:
            times = [t for t in cls.times(parent=parent) if t != time]
            folders.extend([parent/t for t in times])

        for path in folders:
            utils.rmtree(path)

    @classmethod
    def deleteMesh(cls):
        utils.rmtree(cls.polyMeshPath())

    @classmethod
    def latestTimeToZero(cls):
        for parent in [cls._casePath, *cls.processorFolders()]:
            latestTime = cls.latestTime(parent)
            if latestTime == '0':
                continue

            zeroPath = parent / '0'
            latestPath = parent / latestTime

            if latestPath.exists():
                utils.rmtree(zeroPath)
                latestPath.rename(zeroPath)

        cls.deleteCalculationResults('0')

    @classmethod
    def addConstantFileToKeep(cls, fileName):
        cls._constantFilesToKeep.append(fileName)
