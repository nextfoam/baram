#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.mpi import ParallelType, ParallelEnvironment

from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project


def getNP() -> int:
    numCoresStr = Project.instance().np
    if numCoresStr is None:  # ToDo: For compatibility. Remove this code block after 20240601
        numCoresStr = coredb.CoreDB().getValue('.//parallel/numberOfCores')
        Project.instance().np = numCoresStr

    return int(numCoresStr)


def getParallelType() -> ParallelType:
    ptypeStr = Project.instance().pType
    if ptypeStr is None:  # ToDo: For compatibility. Remove this code block after 20240601
        if coredb.CoreDB().getValue('.//parallel/localhost') == 'true':
            ptypeStr = ParallelType.LOCAL_MACHINE.value
        else:
            ptypeStr = ParallelType.CLUSTER.value

        Project.instance().pType = ptypeStr

    return ParallelType(int(ptypeStr))


def getHostfile() -> str:
    hostfile = Project.instance().hostfile
    if hostfile is None:
        hostfile = ''
        Project.instance().hostfile = hostfile

    return hostfile


def getEnvironment():
    return ParallelEnvironment(getNP(), getParallelType(), getHostfile())


def setEnvironment(environment: ParallelEnvironment):
    Project.instance().np = str(environment.np())
    Project.instance().pType = environment.type().value
    Project.instance().hostfile = environment.hosts()
