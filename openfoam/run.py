#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import platform
import subprocess
import psutil
from pathlib import Path
import asyncio

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

    if 'LD_LIBRARY_PATH' not in os.environ:
        os.environ['LD_LIBRARY_PATH'] = ''

    ENV = {
        'WM_PROJECT_DIR': str(OPENFOAM),
        'PATH': os.environ['PATH'],
        'LD_LIBRARY_PATH': library + os.pathsep + os.environ['LD_LIBRARY_PATH']
    }

def openSolverProcess(cmd, casePath, inParallel):
    stdout = open(casePath/'stdout.log', 'a')
    stderr = open(casePath/'stderr.log', 'a')

    if inParallel:
        cmd.append('-parallel')

    p = subprocess.Popen(cmd,
                         env=ENV, cwd=casePath,
                         stdout=stdout, stderr=stderr,
                         creationflags=creationflags,
                         startupinfo=startupinfo)

    stdout.close()
    stderr.close()

    return p

def launchSolverOnWindow(solver: str, casePath: Path, np: int = 1) -> (int, float):
    args = [MPICMD, '-np', str(np), OPENFOAM/'bin'/solver]

    process = openSolverProcess(args, casePath, np > 1)

    ps = psutil.Process(pid=process.pid)
    return ps.pid, ps.create_time()

def launchSolverOnLinux(solver: str, casePath: Path, uuid, np: int = 1) -> (int, float):
    args = [OPENFOAM/'bin'/'baramd', '-project', uuid, '-cmdline', MPICMD, '-np', str(np), OPENFOAM/'bin'/solver]

    openSolverProcess(args, casePath, np > 1)

    processes = [p for p in psutil.process_iter(['pid', 'cmdline', 'create_time']) if uuid in p.info['cmdline']]
    if processes:
        ps = max(processes, key=lambda p: p.create_time())
        return ps.pid, ps.create_time()

    return None

def launchSolver(solver: str, casePath: Path, uuid, np: int = 1) -> (int, float):
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

    if platform.system() == 'Windows':
        return launchSolverOnWindow(solver, casePath, np)
    else:
        return launchSolverOnLinux(solver, casePath, uuid, np)

async def runUtility(program: str, *args, cwd=None):
    global creationflags
    global startupinfo

    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESHOWWINDOW,
            wShowWindow=subprocess.SW_HIDE
        )

    proc = await asyncio.create_subprocess_exec(OPENFOAM/'bin'/program, *args,
                                                env=ENV, cwd=cwd,
                                                creationflags=creationflags,
                                                startupinfo=startupinfo)
    await proc.wait()

    return proc.returncode


def isProcessRunning(pid, startTime):
    if pid and startTime:
        try:
            ps = psutil.Process(pid)
            if ps.create_time() == startTime:
                return True
        except psutil.NoSuchProcess:
            return False

    return False
