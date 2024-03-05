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

from baramFlow.coredb.project import Project
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


def copyDirectory(src, dst):
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


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

        shutil.copytree(resource.file('openfoam/flow_case'), path)

        cls.makeDir(path, Directory.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        cls.makeDir(path, Directory.CONSTANT_DIRECTORY_NAME)

    @classmethod
    def linkLivePolyMeshTo(cls, path, regions, processorOnly = False):
        # To check folders is better than to get "NP" from the configuration
        # to avoid possible mismatch between number of folders and "NP" configuration in the future
        np = len(list(Project.instance().path.joinpath(CASE_DIRECTORY_NAME).glob('processor[0-9]*')))
        processorFolders = [f'processor{i}' for i in range(0, np)]
        if not processorOnly:
            processorFolders.insert(0, '')  # Reconstructed folder

        for processor in processorFolders:
            liveConstant = Project.instance().path / CASE_DIRECTORY_NAME / processor / Directory.CONSTANT_DIRECTORY_NAME
            liveSystem   = Project.instance().path / CASE_DIRECTORY_NAME / processor / Directory.SYSTEM_DIRECTORY_NAME  # noqa: E221

            if not liveConstant.is_dir():
                continue

            batchConstant = path / processor / Directory.CONSTANT_DIRECTORY_NAME
            batchSystem   = path / processor / Directory.SYSTEM_DIRECTORY_NAME  # noqa: E221

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
    def createBatchCase(cls, path, regions):
        cls.createCase(path)

        cls.linkLivePolyMeshTo(path, regions)

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

        return max(times, key=lambda x: float(x))

    @classmethod
    def times(cls, parent: Optional[Path] = None):
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

        return times

    @classmethod
    def polyMeshPath(cls, rname=''):
        return cls.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME

    @classmethod
    def boundaryFilePath(cls, rname):
        return cls.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME / 'boundary'

    @classmethod
    def cellZonesFilePath(cls, rname):
        return cls.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME / 'cellZones'

    @classmethod
    def boundaryDataPath(cls, rname):
        return cls.constantPath(rname) / rname / Directory.BOUNDARY_DATA_DIRECTORY_NAME

    @classmethod
    def postProcessingPath(cls, rname=''):
        return cls._postProcessingPath / rname

    @classmethod
    def foamFilePath(cls):
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
    #
    # @classmethod
    # def _setupNewCase(cls):
    #     if cls._casePath.exists():
    #         utils.rmtree(cls._casePath)
    #
    #     shutil.copytree(resource.file('openfoam/flow_case'), cls._casePath)

    @classmethod
    def _copyMeshFromInternal(cls, directory, regions):
        if cls._constantPath.exists():
            utils.rmtree(cls._constantPath)
        cls._constantPath.mkdir(exist_ok=True)

        srcFile = directory / Directory.REGION_PROPERTIES_FILE_NAME
        if srcFile.is_file():
            shutil.copyfile(srcFile, cls.constantPath(Directory.REGION_PROPERTIES_FILE_NAME))

            for rname in regions:
                srcPath = directory / rname / Directory.POLY_MESH_DIRECTORY_NAME
                objPath = cls.constantPath(rname) / Directory.POLY_MESH_DIRECTORY_NAME
                shutil.copytree(srcPath, objPath, copy_function=shutil.copyfile)
        else:
            polyMeshPath = cls.constantPath(Directory.POLY_MESH_DIRECTORY_NAME)
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
    def saveAs(cls, projectPath, regions):
        liveConstantPath = Project.instance().path / CASE_DIRECTORY_NAME /Directory.CONSTANT_DIRECTORY_NAME

        targetPath = projectPath / CASE_DIRECTORY_NAME
        constantPath = targetPath / Directory.CONSTANT_DIRECTORY_NAME

        cls.createCase(targetPath)
        if liveConstantPath.is_dir():
            if len(regions) > 1:
                srcFile = liveConstantPath / Directory.REGION_PROPERTIES_FILE_NAME
                shutil.copyfile(srcFile, constantPath / Directory.REGION_PROPERTIES_FILE_NAME)

                for rname in regions:
                    shutil.copytree(liveConstantPath / rname, constantPath / rname, copy_function=shutil.copyfile)
            else:
                srcPath = liveConstantPath / Directory.POLY_MESH_DIRECTORY_NAME
                shutil.copytree(srcPath, constantPath / Directory.POLY_MESH_DIRECTORY_NAME,
                                copy_function=shutil.copyfile)

            with open(targetPath / FOAM_FILE_NAME, 'a'):
                pass

    @classmethod
    def initialize(cls, time: str = None):
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

        folders = [cls._postProcessingPath]

        for parent in [cls._casePath, *cls.processorFolders()]:
            times = [t for t in cls.times(parent=parent) if t != time]
            folders.extend([parent/t for t in times])

        for path in folders:
            utils.rmtree(path)

    @classmethod
    def addConstantFileToKeep(cls, fileName):
        cls._constantFilesToKeep.append(fileName)
