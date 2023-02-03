#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import shutil
import uuid
from pathlib import Path


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
    target = p.parent / ('delete_me_' + str(uuid.uuid4()))
    p.rename(target)

    coro = asyncio.to_thread(shutil.rmtree, target, ignore_errors, onerror)
    task = asyncio.create_task(coro)

    _backgroundTasks.add(task)

    task.add_done_callback(_backgroundTasks.discard)

