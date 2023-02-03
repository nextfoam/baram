#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import shutil
import uuid
from pathlib import Path


backgroundTasks = set()


async def _rmtreeBackground(path, ignore_errors=False, onerror=None):
    shutil.rmtree(path, ignore_errors, onerror)


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
    task = asyncio.create_task(_rmtreeBackground(target, ignore_errors, onerror))
    backgroundTasks.add(task)
    task.add_done_callback(backgroundTasks.discard)

