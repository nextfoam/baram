#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform
from enum import IntEnum
from pathlib import Path


class ParallelType(IntEnum):
    LOCAL_MACHINE = 0
    CLUSTER = 1
    SLURM = 2


HOST_FILE_NAME = 'hostfile'
if platform.system() == 'Windows':
    MPICMD = 'mpiexec'
    HOST_FILE_OPTION = '-machinefile'
else:
    MPICMD = 'mpirun'
    HOST_FILE_OPTION = '-hostfile'


class ParallelEnvironment:
    def __init__(self, np, type_, hosts):
        self._np: int = np
        self._type = type_
        self._hosts = hosts

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

    def setType(self, type_):
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
