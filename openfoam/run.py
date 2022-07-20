#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import platform
import subprocess
import psutil
from pathlib import Path

# Solver Directory Structure
#
# solvers/
#     mingw64/ : mingw64 library, only on Windows
#         bin/
#         lib/
#     openfoam/
#         bin/ : solvers reside here
#         lib/
#         etc/ : OpenFOAM system 'etc'

MPICMD = 'mpirun'

OPENFOAM = Path('solvers/openfoam').resolve()

creationflags = 0
startupinfo = None

if platform.system() == 'Windows':
    MPICMD = 'mpiexec'
    MINGW = Path('solvers/mingw64').resolve()
    library = str(OPENFOAM/'lib') + os.pathsep \
              + str(OPENFOAM/'lib'/'msmpi') + os.pathsep \
              + str(MINGW/'bin') + os.pathsep \
              + str(MINGW/'lib')
    creationflags = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
            | subprocess.CREATE_NEW_PROCESS_GROUP
    )
    startupinfo = subprocess.STARTUPINFO(
        dwFlags = subprocess.STARTF_USESHOWWINDOW,
        wShowWindow = subprocess.SW_HIDE
    )
    ENV = {
        'WM_PROJECT_DIR': str(OPENFOAM),
        'PATH': library + os.pathsep + os.environ['PATH']
    }
else:
    library = str(OPENFOAM/'lib') + os.pathsep \
              + str(OPENFOAM/'lib'/'sys-openmpi/')
    ENV = {
        'WM_PROJECT_DIR': str(OPENFOAM),
        'PATH': os.environ['PATH'],
        'LD_LIBRARY_PATH': library + os.pathsep + os.environ['LD_LIBRARY_PATH']
    }


def launchSolver(solver: str, casePath: Path, np: int = 1) -> (int, float):
    """Launch solver

    Launch solver in case folder
    Solver runs by mpirun/mpiexec by default

    Solver standard output file
        casePath/stdout.log
    Solver standard error file
        casePath/stderr.log

    Args:
        solver: solver name
        casePath: case folder absolute path
        np: number of process

    Returns:
        pid: process id of mpirun/mpiexec
        create_time: process creation time
    """
    if not isinstance(casePath, Path) or not casePath.is_absolute():
        raise AssertionError

    stdout = open(casePath/'stdout.log', 'w')
    stderr = open(casePath/'stderr.log', 'w')

    p = subprocess.Popen([MPICMD, '-np', str(np), OPENFOAM/'bin'/solver],
                         env=ENV, cwd=casePath,
                         stdout=stdout, stderr=stderr,
                         creationflags=creationflags,
                         startupinfo=startupinfo)

    stdout.close()
    stderr.close()

    ps = psutil.Process(pid=p.pid)
    return ps.pid, ps.create_time()

