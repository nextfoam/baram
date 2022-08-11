#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication

from coredb.coredb import CoreDB, Error


@dataclass
class DBWriteItem:
    xpath: str
    value: str
    name: str
    isAttribute: bool = False


class DBWriterError:
    def __init__(self, name, error):
        self._name = name
        self._error = error

    def toMessage(self):
        if self._error == Error.OUT_OF_RANGE:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} is out of range.')
        elif self._error == Error.INTEGER_ONLY:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} must be a integer.')
        elif self._error == Error.FLOAT_ONLY:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} must be a float.')
        elif self._error == Error.REFERENCED:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} is referenced by another.')


class CoreDBWriter:
    def __init__(self):
        self._items = []
        self._errors = None

        self._db = CoreDB()

    def append(self, xpath, value, label):
        self._items.append(DBWriteItem(xpath, value, label))

    def setAttribute(self, xpath, name, value):
        self._items.append(DBWriteItem(xpath, value, name, True))

    def write(self):
        self._errors = []
        with self._db:
            for i in self._items:
                error = None
                if i.isAttribute:
                    self._db.setAttribute(i.xpath, i.name, i.value)
                else:
                    error = self._db.setValue(i.xpath, i.value)

                if error is not None:
                    self._errors.append(DBWriterError(i.name, error))

        return len(self._errors)

    def firstError(self):
        return self._errors[0]

