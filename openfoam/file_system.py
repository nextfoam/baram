#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import asyncio
from pathlib import Path

from coredb.project import Project

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile


class FileSystem:
    CASE_DIRECTORY_NAME = 'case'
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLY_MESH_DIRECTORY_NAME = 'polyMesh'
    BOUNDARY_DATA_DIRECTORY_NAME = 'boundaryData'

    _casePath = None
    _constantPath = None
    _boundaryConditionsPath = None
    _systemPath = None

    @classmethod
    def setup(cls):
        cls._casePath = cls.makeDir(Project.instance().path, cls.CASE_DIRECTORY_NAME)
        cls._constantPath = os.path.join(cls._casePath, cls.CONSTANT_DIRECTORY_NAME)

    @classmethod
    def initCaseDir(cls):
        cls._boundaryConditionsPath = cls.makeDir(cls._casePath, cls.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        cls._systemPath = cls.makeDir(cls._casePath, cls.SYSTEM_DIRECTORY_NAME)

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
        return os.path.join(cls._constantPath, rname) if rname else cls._constantPath

    @classmethod
    def boundaryConditionsPath(cls, rname=None):
        return os.path.join(cls._boundaryConditionsPath, rname) if rname else cls._boundaryConditionsPath

    @classmethod
    def systemPath(cls, rname=None):
        return os.path.join(cls._systemPath, rname) if rname else cls._systemPath

    @classmethod
    def boundaryFilePath(cls, rname):
        return os.path.join(cls.constantPath(rname), cls.POLY_MESH_DIRECTORY_NAME, 'boundary')

    @classmethod
    def cellZonesFilePath(cls, rname):
        return os.path.join(cls.constantPath(rname), cls.POLY_MESH_DIRECTORY_NAME, 'cellZones')

    @classmethod
    def boundaryDataPath(cls, rname):
        return os.path.join(cls.constantPath(rname), rname, cls.BOUNDARY_DATA_DIRECTORY_NAME)

    @classmethod
    def foamFilePath(cls):
        return Path(os.path.join(cls._casePath, 'baram.foam'))

    @classmethod
    def _copyMeshFromInternal(cls, directory, multiRegionState):
        if os.path.exists(cls._constantPath):
            shutil.rmtree(cls._constantPath)

        constantPath = cls._constantPath
        Path(constantPath).mkdir(parents=True)
        if multiRegionState:
            srcFile = f'{directory}/regionProperties'
            objFile = f'{constantPath}/regionProperties'
            shutil.copyfile(srcFile, objFile)

            regions = []
            regionsDict = ParsedParameterFile(f'{directory}/regionProperties').content['regions']
            for i in range(1, len(regionsDict), 2):
                for region in regionsDict[i]:
                    regions.append(region)

            for d in regions:
                srcPath = f'{directory}/{d}'
                objPath = f'{constantPath}/{d}'
                shutil.copytree(srcPath, objPath, dirs_exist_ok=True)

        elif not multiRegionState:
            polyMeshPath = f'{cls._constantPath}/polyMesh'
            Path(polyMeshPath).mkdir(parents=True)


            shutil.copytree(directory, polyMeshPath, dirs_exist_ok=True)

        with open(cls.foamFilePath(), 'a'):
            pass

    @classmethod
    async def copyMeshFrom(cls, directory, multiRegionState):
        await asyncio.to_thread(cls._copyMeshFromInternal, directory, multiRegionState)

    @classmethod
    def makeDir(cls, parent, directory):
        path = os.path.join(parent, directory)
        if not os.path.exists(path):
            os.mkdir(path)
        return path
