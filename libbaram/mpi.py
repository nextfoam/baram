#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform
import re
from enum import IntEnum, auto
from pathlib import Path

import asyncio
from libbaram.process import runExternalCommand


class ParallelType(IntEnum):
    LOCAL_MACHINE = 0
    CLUSTER = 1
    SLURM = 2


class MPIStatus(IntEnum):
    OK = 0
    NOT_FOUND = auto()
    LOW_VERSION = auto()


HOST_FILE_NAME = 'hostfile'
if platform.system() == 'Windows':
    MPICMD = 'mpiexec'
    HOST_FILE_OPTION = '-machinefile'
    VERSION_CHECK_OPTION = '-help'
    MAJOR_VERSION = 10
    MINOR_VERSION = 1
else:
    MPICMD = 'mpirun'
    HOST_FILE_OPTION = '-hostfile'
    VERSION_CHECK_OPTION = '--version'
    MAJOR_VERSION = 4
    MINOR_VERSION = 1


async def checkMPI():
    try:
        process = await runExternalCommand(MPICMD, VERSION_CHECK_OPTION,
                                          stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        m = re.search('([0-9]+)\.([0-9]+)\.', stdout.decode())
        major = int(m.group(1))
        minor = int(m.group(2))

        # if major < MAJOR_VERSION or (major == MAJOR_VERSION and minor < MINOR_VERSION):
        if major < MAJOR_VERSION:
            return MPIStatus.LOW_VERSION

        return MPIStatus.OK
    except FileNotFoundError:
        return MPIStatus.NOT_FOUND


class ParallelEnvironment:
    def __init__(self, np: int, type_: ParallelType, hosts: str):
        self._np: int = np
        self._type = type_
        self._hosts = '' if hosts is None else hosts

    def np(self):
        return self._np

    def type(self):
        return self._type

    def hosts(self):
        return self._hosts

    def isParallelOn(self):
        return self._np > 1

    def setNP(self, np: int):
        self._np = np

    def setType(self, type_: ParallelType):
        self._type = type_

    def setHosts(self, hosts):
        self._hosts = hosts

    def makeCommand(self, *command, cwd: Path, options):
        # windows: mpiexec
        # others: mpirun
        cmdline = [MPICMD]

        if self._type == ParallelType.CLUSTER:
            # windows: -env <name_1> <value_1> ... -env <name_n> <value_n>
            # others: -x <name_1> ... -x <name_n>
            cmdline.extend(options)

            if self._hosts:
                path = cwd / HOST_FILE_NAME
                with path.open(mode='w') as f:
                    f.write(self._hosts)

                # windows: -machinefile $cwd/hostfile
                # others: -hostfile $cwd/hostfile
                cmdline.append(HOST_FILE_OPTION)
                cmdline.append(str(path))

        # -np <N>
        cmdline.append('-np')
        cmdline.append(str(self._np))

        # <program command to run>
        cmdline.extend(command)

        if self._np > 1:
            # -parallel
            cmdline.append('-parallel')

        return cmdline
