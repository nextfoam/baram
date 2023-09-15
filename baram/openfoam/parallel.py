#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum

from baram.coredb import coredb
from baram.coredb.project import Project


class ParallelType(IntEnum):
    LOCAL_MACHINE = 0
    CLUSTER = 1
    SLURM = 2


def getNP() -> int:
    numCoresStr = Project.instance().np
    if numCoresStr is None:  # For compatibility. Remove this block after 20240601
        numCoresStr = coredb.CoreDB().getValue('.//parallel/numberOfCores')
        Project.instance().np = numCoresStr

    return int(numCoresStr)


def setNP(np: int):
    Project.instance().np = str(np)


def getParallelType() -> ParallelType:
    ptypeStr = Project.instance().pType
    if ptypeStr is None:  # For compatibility. Remove this block after 20240601
        if coredb.CoreDB().getValue('.//parallel/localhost') == 'true':
            ptypeStr = ParallelType.LOCAL_MACHINE.value
        else:
            ptypeStr = ParallelType.CLUSTER.value

        Project.instance().pType = ptypeStr

    return ParallelType(int(ptypeStr))


def setParallelType(type_: ParallelType):
    Project.instance().pType = type_.value


def getHostfile() -> str:
    hostfile = Project.instance().hostfile
    if hostfile is None:
        hostfile = ''
        Project.instance().hostfile = hostfile

    return hostfile


def setHostfile(hostfile: str):
    Project.instance().hostfile = hostfile
