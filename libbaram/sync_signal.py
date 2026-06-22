#!/usr/bin/env python
# -*- coding: utf-8 -*-

import types
from typing import Callable, Optional
import weakref


class SyncSignal():
    def __init__(self, *param_types):
        if not all(isinstance(t, (type, types.GenericAlias)) for t in param_types):
            raise AssertionError('Only "Type" class is allowed')

        self._types = param_types
        self._callbacks: dict[Callable, Optional[weakref.ref]] = {}

    def connect(self, func: Callable, obj=None):
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

    def emit(self, *args, **kwargs):
        if len(args) != len(self._types):
            raise AssertionError('Wrong number of Parameters')

        for arg, type_ in zip(args, self._types):
            if not isinstance(arg, type_):
                raise AssertionError('Wrong parameter type')

        dead = []
        for cb, wref in self._callbacks.items():
            if wref is None or wref() is not None:
                cb(*args, **kwargs)
            else:
                dead.append(cb)

        for cb in dead:
            del self._callbacks[cb]


def main():
    signal = SyncSignal(str, int)
    signal.emit('test', 1)

    signal = SyncSignal(str)
    signal.emit('test')

    signal = SyncSignal()
    signal.emit()


if __name__ == '__main__':
    main()
