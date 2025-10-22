#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import subprocess

import psutil
from pathlib import Path
import asyncio

from libbaram.mpi import ParallelEnvironment

from libbaram.app_path import APP_PATH
from libbaram.process import RunSubprocess

# Solver Directory Structure
#
# solvers/
#     mingw64/ : mingw64 library, only on Windows
#         bin/
#         lib/
#     openfoam/
#         bin/ : solvers reside here
#         lib/
#         lib/sys-openmpi
#         lib/dummy
#         etc/ : OpenFOAM system 'etc'
#         tlib/ : Third-Party Library, only for Linux and macOS



# MPICMD = 'mpirun'

OPENFOAM = APP_PATH / 'solvers' / 'openfoam'

creationflags = 0
startupinfo = None

STDOUT_FILE_NAME = 'stdout.log'
STDERR_FILE_NAME = 'stderr.log'

WM_PROJECT_DIR = str(OPENFOAM)

if platform.system() == 'Windows':
    # MPICMD = 'mpiexec'
    MINGW = APP_PATH / 'solvers' / 'mingw64'
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
        dwFlags=subprocess.STARTF_USESHOWWINDOW,
        wShowWindow=subprocess.SW_HIDE
    )

    PATH = library + os.pathsep + os.environ['PATH']

    ENV = os.environ.copy()
    ENV.update({
        'WM_PROJECT_DIR': WM_PROJECT_DIR,
        'PATH': PATH
    })

    MPI_OPTIONS = ['-env', 'WM_PROJECT_DIR', WM_PROJECT_DIR, '-env', 'PATH', PATH]
else:
    library = str(OPENFOAM/'lib') + os.pathsep \
              + str(OPENFOAM/'lib'/'sys-openmpi') + os.pathsep \
              + str(OPENFOAM/'lib'/'dummy') + os.pathsep \
              + str(OPENFOAM/'tlib')

    if platform.system() == 'Darwin':
        library += os.pathsep + '/opt/homebrew/lib'
        library = str(APP_PATH) + os.pathsep + library  # APP_PATH should be at the front to get priority

    if platform.system() == 'Darwin':
        LIBRARY_PATH_NAME = 'DYLD_LIBRARY_PATH'
    else:
        LIBRARY_PATH_NAME = 'LD_LIBRARY_PATH'

    if LIBRARY_PATH_NAME not in os.environ:
        os.environ[LIBRARY_PATH_NAME] = ''

    LIBRARY_PATH = library + os.pathsep + os.environ[LIBRARY_PATH_NAME]

    ENV = os.environ.copy()
    ENV.update({
        'WM_PROJECT_DIR': WM_PROJECT_DIR,
        LIBRARY_PATH_NAME: LIBRARY_PATH
    })

    if platform.system() == 'Darwin':
        PATH = '/opt/homebrew/bin' + os.pathsep + os.environ['PATH']
        ENV.update({
            'PATH': PATH,
            'DYLD_FALLBACK_LIBRARY_PATH': LIBRARY_PATH,  # To find libraries for function objects
            'FOAM_LD_LIBRARY_PATH': library
        })

    MPI_OPTIONS = ['-x', 'WM_PROJECT_DIR', '-x', LIBRARY_PATH_NAME]


def openSolverProcess(cmd, casePath):
    stdout = open(casePath / STDOUT_FILE_NAME, 'w')
    stderr = open(casePath / STDERR_FILE_NAME, 'w')

    p = subprocess.Popen(cmd,
                         env=ENV, cwd=casePath,
                         stdout=stdout, stderr=stderr,
                         creationflags=creationflags,
                         startupinfo=startupinfo)

    stdout.close()
    stderr.close()

    return p


def launchSolverOnWindow(solver: str, casePath: Path, parallel: ParallelEnvironment) -> (int, float):
    process = openSolverProcess(
        parallel.makeCommand(OPENFOAM / 'bin' / solver, cwd=casePath, options=MPI_OPTIONS), casePath)

    ps = psutil.Process(pid=process.pid)
    return ps.pid, ps.create_time()


def launchSolverOnLinux(solver: str, casePath: Path, uuid, parallel: ParallelEnvironment) -> (int, float):
    args = [OPENFOAM/'bin'/'baramd', '-project', uuid, '-cmdline']
    args.extend(parallel.makeCommand(OPENFOAM / 'bin' / solver, cwd=casePath, options=MPI_OPTIONS))

    process = openSolverProcess(args, casePath)
    process.wait()

    processes = [p for p in psutil.process_iter(['pid', 'cmdline', 'create_time'])
                 if (p.info['cmdline'] is not None) and (uuid in p.info['cmdline'])]
    if processes:
        ps = max(processes, key=lambda p: p.create_time())
        return ps.pid, ps.create_time()

    return None


def launchSolver(solver: str, casePath: Path, uuid, parallel: ParallelEnvironment) -> (int, float):
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
        uuid: UUID for the process
        parallel: Parallel Environment

    Returns:
        pid: process id of mpirun/mpiexec
        create_time: process creation time
    """
    if not isinstance(casePath, Path) or not casePath.is_absolute():
        raise AssertionError

    if platform.system() == 'Windows':
        return launchSolverOnWindow(solver, casePath, parallel)
    else:
        return launchSolverOnLinux(solver, casePath, uuid, parallel)


async def runUtility(program: str, *args, cwd=None, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL):
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
                                                startupinfo=startupinfo,
                                                stdout=stdout,
                                                stderr=stderr)

    return proc


class RunUtility(RunSubprocess):
    def __init__(self, program: str, *args, cwd: Path = None, useVenv=True, parallel: ParallelEnvironment = None):
        super().__init__(program, *args, cwd=cwd, useVenv=useVenv)

        self._parallel = parallel

    async def start(self):
        global creationflags
        global startupinfo

        if platform.system() == 'Windows':
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO(
                dwFlags=subprocess.STARTF_USESHOWWINDOW,
                wShowWindow=subprocess.SW_HIDE
            )

        if self._parallel is None:
            self._proc = await asyncio.create_subprocess_exec(OPENFOAM/'bin'/self._program, *self._args,
                                                              env=ENV, cwd=self._cwd,
                                                              creationflags=creationflags,
                                                              startupinfo=startupinfo,
                                                              stdout=asyncio.subprocess.PIPE,
                                                              stderr=asyncio.subprocess.PIPE)
        else:
            self._proc = await asyncio.create_subprocess_exec(
                *self._parallel.makeCommand(OPENFOAM / 'bin' / self._program, *self._args, cwd=self._cwd, options=MPI_OPTIONS),
                env=ENV, cwd=self._cwd, creationflags=creationflags, startupinfo=startupinfo, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


async def runParallelUtility(program: str, *args, parallel: ParallelEnvironment, cwd: Path = None,
                             stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL):
    global creationflags
    global startupinfo

    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESHOWWINDOW,
            wShowWindow=subprocess.SW_HIDE
        )

    proc = await asyncio.create_subprocess_exec(
        *parallel.makeCommand(OPENFOAM / 'bin' / program, *args, cwd=cwd, options=MPI_OPTIONS),
        env=ENV, cwd=cwd, creationflags=creationflags, startupinfo=startupinfo, stdout=stdout, stderr=stderr)

    return proc


def hasUtility(program: str):
    return (OPENFOAM / 'bin' / program).is_file()


class OpenFOAMError(Exception):
    def __init__(self, returncode, message):
        super().__init__(returncode, message)


class RunParallelUtility(RunUtility):
    pass


async def openTerminal(cwd: Path):
    env = ENV.copy()
    paths = env['PATH'].split(os.pathsep)
    paths.append(str(OPENFOAM/'bin'))

    if 'VIRTUAL_ENV' in env:
        vpath = env['VIRTUAL_ENV']
        env['PATH'] = os.pathsep.join([p for p in paths if not p.startswith(vpath)])

    vvars = ['VIRTUAL_ENV', 'PYTHONHOME', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV']
    for var in vvars:
        env.pop(var, None)

    system = platform.system()

    if system == "Windows":
        env.pop('PROMPT', None)

        try:
            # Windows Terminal
            process = await asyncio.create_subprocess_exec("wt.exe", "--inheritEnvironment", "-d", str(cwd), env=env, cwd=cwd)
        except FileNotFoundError:
            # Fallback to PowerShell
            process = await asyncio.create_subprocess_exec("powershell.exe", env=env, cwd=cwd)
            
        await process.wait()

    elif system == "Darwin":  # macOS
        env.pop('PS1', None)

        process = await asyncio.create_subprocess_exec("open", "-a", "Terminal", env=env, cwd=cwd)
        await process.wait()

    elif system == "Linux":
        env.pop('PS1', None)

        process = None
        terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
        for terminal in terminals:
            try:
                process = await asyncio.create_subprocess_exec(terminal, env=env, cwd=cwd)
                await process.wait()
                break
            except FileNotFoundError:
                continue

        if process is None:
            raise RuntimeError("No suitable terminal emulator found")

    else:
        raise OSError(f"Unsupported operating system: {system}")

