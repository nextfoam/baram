#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import types
import weakref
from typing import Callable, Optional, get_origin


class AsyncSignal():
    def __init__(self, *param_types):
        if not all(isinstance(t, (type, types.GenericAlias)) for t in param_types):
            raise AssertionError('Only "Type" class is allowed')

        self._types = param_types
        self._callbacks: dict[Callable, Optional[weakref.ref]] = {}
        self._pending_tasks: set[asyncio.Task] = set()

    def asyncConnect(self, func: Callable, obj=None):
        if not asyncio.iscoroutinefunction(func):
            raise AssertionError('Not corouting function')

        if func in self._callbacks:
            raise AssertionError('Already connected')

        if obj is not None:
            self._callbacks[func] = weakref.ref(obj)
        else:
            self._callbacks[func] = None

    def disconnect(self, func: Callable):
        if func not in self._callbacks:
            raise AssertionError('Not connected')

        del self._callbacks[func]

    async def emit(self, *args, **kwargs):
        if len(args) != len(self._types):
            raise AssertionError('Wrong number of Parameters')

        for arg, type_ in zip(args, self._types):
            if not isinstance(arg, get_origin(type_) or type_):
                raise AssertionError('Wrong parameter type')

        dead = []
        for cb, wref in self._callbacks.items():
            if wref is None or wref() is not None:
                await cb(*args, **kwargs)
            else:
                dead.append(cb)

        for cb in dead:
            del self._callbacks[cb]

    def emitLater(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        dead = []
        for cb, wref in self._callbacks.items():
            if wref is None or wref() is not None:
                task = loop.create_task(cb(*args, **kwargs))
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)
            else:
                dead.append(cb)

        for cb in dead:
            del self._callbacks[cb]


async def main():
    signal = AsyncSignal(str, int)
    await signal.emit('test', 1)

    signal = AsyncSignal(str)
    await signal.emit('test')

    signal = AsyncSignal()
    await signal.emit()


if __name__ == '__main__':
    asyncio.run(main())
