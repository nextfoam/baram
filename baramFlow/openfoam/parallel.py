#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.mpi import ParallelType, ParallelEnvironment

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project


def getNP() -> int:
    numCoresStr = Project.instance().np
    return int(numCoresStr)


def getParallelType() -> ParallelType:
    ptypeStr = Project.instance().pType
    return ParallelType(ptypeStr) if isinstance(ptypeStr, int) else ParallelType[ptypeStr]


def getHostfile() -> str:
    return Project.instance().hostfile


def getEnvironment():
    return ParallelEnvironment(getNP(), getParallelType(), getHostfile())


def setEnvironment(environment: ParallelEnvironment):
    Project.instance().setParallelEnvironment(environment)
