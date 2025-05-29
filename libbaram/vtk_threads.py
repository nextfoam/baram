#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import functools
import contextvars
from concurrent.futures import ThreadPoolExecutor


_pool = ThreadPoolExecutor(1)  # To make only one thread running for VTK

# vtkThreadLock = asyncio.Lock()
vtkThreadLock: asyncio.Lock = None  # it should be initialized in main as soon as main loop is created


# Copied from asyncio.to_thread
async def _to_vtk_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(_pool, func_call)


_holdRendering = False


def holdRendering():
    """Holds VTK rendering while VTK is working in background

    Raises:
        AssertionError: Rendering is already on hold
    """
    global _holdRendering

    if _holdRendering:
        raise AssertionError

    _holdRendering = True


def resumeRendering():
    """Resume VTK rendering

    Raises:
        AssertionError: Rendering is not hold
    """
    global _holdRendering

    if not _holdRendering:
        raise AssertionError

    _holdRendering = False


def isRenderingHold():
    return _holdRendering


async def vtk_run_in_thread(func, /, *args, **kwargs):
    async with vtkThreadLock:
        holdRendering()
        await _to_vtk_thread(func, *args, **kwargs)
        resumeRendering()
