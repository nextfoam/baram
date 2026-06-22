#!/usr/bin/env python
# -*- coding: utf-8 -*-


from threading import Lock

from baramFlow.coredb import coredb


_mutex = Lock()


class UserParameters:
    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(UserParameters, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        self._arguments: dict[str, str] = {}

    def setParameters(self, arguments=None):
        self._arguments = coredb.CoreDB().getBatchDefaults()
        if arguments:
            self._arguments.update(arguments)

    def getValue(self, parameter: str):
        return self._arguments[parameter]



