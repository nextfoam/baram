#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import asyncio
from typing import Optional
from pathlib import Path

from coredb.project import Project
from libbaram import utils


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
    TEMP_DIRECTORY_NAME = 'temp'
    CASE_DIRECTORY_NAME = 'case'
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLY_MESH_DIRECTORY_NAME = 'polyMesh'
    BOUNDARY_DATA_DIRECTORY_NAME = 'boundaryData'
    REGION_PROPERTIES_FILE_NAME = 'regionProperties'
    FOAM_FILE_NAME = 'baram.foam'
    POST_PROCESSING_DIRECTORY_NAME = 'postProcessing'

    _casePath: Optional[Path] = None
    _constantPath = None
    _boundaryConditionsPath = None
    _systemPath = None
    _postProcessingPath = None

    _caseFilesToKeep = [
        CONSTANT_DIRECTORY_NAME,
        SYSTEM_DIRECTORY_NAME,
        FOAM_FILE_NAME,
        # BOUNDARY_CONDITIONS_DIRECTORY_NAME
    ]
    _constantFilesToKeep = [POLY_MESH_DIRECTORY_NAME, REGION_PROPERTIES_FILE_NAME]

    @classmethod
    def createCase(cls):
        cls._setCaseRoot(Project.instance().path / cls.TEMP_DIRECTORY_NAME)
        if cls._casePath.exists():
            utils.rmtree(cls._casePath)

        cls._casePath.mkdir(exist_ok=True)
        cls._setupNewCase()

    @classmethod
    def setupForProject(cls):
        cls._setCaseRoot(Project.instance().path / cls.CASE_DIRECTORY_NAME)

    @classmethod
    def initRegionDirs(cls, rname):
        cls.makeDir(cls._boundaryConditionsPath, rname)
        cls.makeDir(cls._constantPath, rname)
        cls.makeDir(cls._systemPath, rname)

    @classmethod
    def caseRoot(cls):
        return cls._casePath

    @classmethod
    def constantPath(cls, rname=None):
        return cls._constantPath / rname if rname else cls._constantPath

    @classmethod
    def boundaryConditionsPath(cls, rname=None):
        return cls._boundaryConditionsPath / rname if rname else cls._boundaryConditionsPath

    @classmethod
    def systemPath(cls, rname=None):
        return cls._systemPath / rname if rname else cls._systemPath

    @classmethod
    def boundaryFilePath(cls, rname):
        return cls.constantPath(rname) / cls.POLY_MESH_DIRECTORY_NAME / 'boundary'

    @classmethod
    def cellZonesFilePath(cls, rname):
        return cls.constantPath(rname) / cls.POLY_MESH_DIRECTORY_NAME / 'cellZones'

    @classmethod
    def boundaryDataPath(cls, rname):
        return cls.constantPath(rname) / rname / cls.BOUNDARY_DATA_DIRECTORY_NAME

    @classmethod
    def postProcessingPath(cls, rname):
        return cls._postProcessingPath / rname if rname else cls._postProcessingPath

    @classmethod
    def foamFilePath(cls):
        return cls._casePath / cls.FOAM_FILE_NAME

    @classmethod
    def processorPath(cls, no):
        path = (cls._casePath / f'processor{no}')

        return path if path.is_dir() else None

    @classmethod
    def makeDir(cls, parent, directory):
        path = parent / directory
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def isPolyMesh(cls, path: Path):
        checkFiles = ['boundary', 'faces', 'neighbour', 'owner', 'points']
        for f in checkFiles:
            if path.joinpath(f).is_file() or path.joinpath(f'{f}.gz').is_file():
                continue
            else:
                return False
        return True

    @classmethod
    def processorFolders(cls):
        return list(cls._casePath.glob('processor[0-9]*'))

    @classmethod
    def numberOfProcessorFolders(cls):
        return len(cls.processorFolders())

    @classmethod
    def _setupNewCase(cls):
        with open(cls.foamFilePath(), 'a'):
            pass

        cls._boundaryConditionsPath = cls.makeDir(cls._casePath, cls.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        cls._systemPath = cls.makeDir(cls._casePath, cls.SYSTEM_DIRECTORY_NAME)
        cls._constantPath = cls.makeDir(cls._casePath, cls.CONSTANT_DIRECTORY_NAME)

    @classmethod
    def _copyMeshFromInternal(cls, directory, regions):
        if cls._constantPath.exists():
            utils.rmtree(cls._constantPath)
        cls._constantPath.mkdir(exist_ok=True)

        srcFile = directory / cls.REGION_PROPERTIES_FILE_NAME
        if srcFile.is_file():
            objFile = cls.constantPath(cls.REGION_PROPERTIES_FILE_NAME)
            shutil.copyfile(srcFile, objFile)

            for rname in regions:
                srcPath = directory / rname / cls.POLY_MESH_DIRECTORY_NAME
                objPath = cls.constantPath(rname) / cls.POLY_MESH_DIRECTORY_NAME
                shutil.copytree(srcPath, objPath, copy_function=shutil.copyfile)
        else:
            polyMeshPath = cls.constantPath(cls.POLY_MESH_DIRECTORY_NAME)
            shutil.copytree(directory, polyMeshPath, copy_function=shutil.copyfile)

    @classmethod
    async def copyMeshFrom(cls, directory, regions):
        await asyncio.to_thread(cls._copyMeshFromInternal, directory, regions)

    @classmethod
    async def copyFileToCase(cls, file):
        await asyncio.to_thread(shutil.copyfile, file, cls._casePath / file.name)

    @classmethod
    async def removeFile(cls, file):
        path = cls._casePath / file
        path.unlink()

    @classmethod
    def save(cls):
        targetPath = Project.instance().path / cls.CASE_DIRECTORY_NAME
        if cls._casePath != targetPath:
            if targetPath.exists():
                utils.rmtree(targetPath)
            cls._casePath.rename(targetPath)
            cls._setCaseRoot(targetPath)

    @classmethod
    def saveAs(cls, projectPath):
        targetPath = projectPath / cls.CASE_DIRECTORY_NAME
        if cls._casePath.exists():
            shutil.copytree(cls._casePath, targetPath, dirs_exist_ok=True)
        cls._setCaseRoot(targetPath)

    @classmethod
    async def initialize(cls, regions, time: str = None):
        ###
        ### This corresponds to a feature of "preserving last calculation result".
        ### The feature will be provided in other form in the future,
        ### and the code is commented/preserved for now.
        ###
        # latestTimeDir = cls._casePath / '-1'
        # keepFiles = [cls.CONSTANT_DIRECTORY_NAME, cls.SYSTEM_DIRECTORY_NAME, cls.FOAM_FILE_NAME]
        # for file in cls._casePath.glob('*'):
        #     if file.is_dir and file.name.isnumeric():
        #         if float(file.name) > float(latestTimeDir.name):
        #             shutil.rmtree(latestTimeDir, ignore_errors=True)
        #             latestTimeDir = file
        #         else:
        #             shutil.rmtree(file)
        #     elif file.name not in keepFiles:
        #         cls._remove(file)
        # if latestTimeDir != cls._boundaryConditionsPath:
        #     latestTimeDir.replace(cls._boundaryConditionsPath)

        def clearConstant(path):
            constantPath = path / cls.CONSTANT_DIRECTORY_NAME
            if len(regions) > 1:
                for file in constantPath.glob('*'):
                    if file.name in regions:
                        clearDirectory(file, cls._constantFilesToKeep)
                    elif file.name not in cls._constantFilesToKeep:
                        remove(file)

        if time is None:
            clearDirectory(cls._casePath, cls._caseFilesToKeep)
        else:
            for f in cls._casePath.glob('*'):
                if f.name not in cls._caseFilesToKeep and f.name != time and not f.name.startswith('processor'):
                    remove(f)

            for processor in cls.processorFolders():
                clearDirectory(processor, cls._caseFilesToKeep, time)
                clearConstant(processor)

        clearConstant(cls._casePath)
        clearDirectory(cls._systemPath, ['controlDict'])

    @classmethod
    def addConstantFileToKeep(cls, fileName):
        cls._constantFilesToKeep.append(fileName)

    @classmethod
    def _setCaseRoot(cls, path):
        cls._casePath = path
        cls._constantPath = cls._casePath / cls.CONSTANT_DIRECTORY_NAME
        cls._boundaryConditionsPath = cls._casePath / cls.BOUNDARY_CONDITIONS_DIRECTORY_NAME
        cls._systemPath = cls._casePath / cls.SYSTEM_DIRECTORY_NAME
        cls._postProcessingPath = cls._casePath / cls.POST_PROCESSING_DIRECTORY_NAME
