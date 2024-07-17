#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import os
import platform
import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QRect

_backgroundTasks = set()


def rmtree(path, ignore_errors=False, onerror=None):
    """Delete file tree immediately and safely in the background

    This function renames the path into temporary one and delete the path in the background

    Args:
        path:
        ignore_errors:
        onerror:

    Returns:

    """
    p = Path(path)
    if not p.exists():
        return

    target = p.parent / ('delete_me_' + str(uuid.uuid4()))
    p.rename(target)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # This function might be called in a thread
        loop = None

    if loop is not None:
        coro = asyncio.to_thread(shutil.rmtree, target, ignore_errors, onerror)
        task = asyncio.create_task(coro)

        _backgroundTasks.add(task)

        task.add_done_callback(_backgroundTasks.discard)
    else:  # loop is None
        shutil.rmtree(target, ignore_errors, onerror)


def getFit(window: QRect, display: QRect) -> QRect:
    x, y, width, height = window.getRect()

    if x < display.topLeft().x():
        x = display.topLeft().x()
    if y < display.topLeft().y():
        y = display.topLeft().y()

    # Note that "width" and "height" are scaled by "QT_SCALE_FACTOR"
    if width > display.width():
        width = display.width()
    if height > display.height() - 40:  # "40" for window title bar
        height = display.height() - 40

    if x + width > display.bottomRight().x():
        x = display.bottomRight().x() - width
    if y + height > display.bottomRight().y():
        y = display.bottomRight().y() - height

    return QRect(x, y, width, height)


def copyOrLink(source: Path, target: Path):
    if platform.system() == 'Windows':
        shutil.copy(source, target)
    else:
        target.symlink_to(os.path.relpath(source, target.parent))  # "walk_up" option for pathlib.Path.relative_to() is not available in python 3.9
