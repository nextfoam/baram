#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.mpi import ParallelType, ParallelEnvironment

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project


def getNP() -> int:
    numCoresStr = Project.instance().np
    if numCoresStr is None:  # ToDo: For compatibility. Remove this code block after 20240601
        numCoresStr = coredb.CoreDB().getValue('/runCalculation/parallel/numberOfCores')

    return int(numCoresStr)


def getParallelType() -> ParallelType:
    ptypeStr = Project.instance().pType
    if ptypeStr is None:  # ToDo: For compatibility. Remove this code block after 20240601
        if coredb.CoreDB().getValue('/runCalculation/parallel/localhost') == 'true':
            return ParallelType.LOCAL_MACHINE
        else:
            return ParallelType.CLUSTER
        
    return ParallelType(ptypeStr) if isinstance(ptypeStr, int) else ParallelType[ptypeStr]


def getHostfile() -> str:
    return Project.instance().hostfile


def getEnvironment():
    return ParallelEnvironment(getNP(), getParallelType(), getHostfile())


def setEnvironment(environment: ParallelEnvironment):
    Project.instance().setParallelEnvironment(environment)
