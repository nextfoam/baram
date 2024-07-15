#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb.coredb import CoreDB, DBError, ValueException


def boolToDBText(value):
    return 'true' if value else 'false'


class WriteItem:
    def __init__(self, xpath, label=None):
        self._xpath = xpath
        self._label = label

    @property
    def label(self):
        return self._label


class ValueSet(WriteItem):
    def __init__(self, xpath, value, label):
        super().__init__(xpath, label)
        self._value = value

    def apply(self, db):
        return db.setValue(self._xpath, self._value)


class AttributeSet(WriteItem):
    def __init__(self, xpath, name, value):
        super().__init__(xpath)
        self._name = name
        self._value = value

    def apply(self, db):
        return db.setAttribute(self._xpath, self._name, self._value)


class ElementAdd(WriteItem):
    def __init__(self, xpath, element, label):
        super().__init__(xpath, label)
        self._element = element

    def apply(self, db):
        return db.addElementFromString(self._xpath, self._element)


class ElementRemove(WriteItem):
    def __init__(self, xpath):
        super().__init__(xpath)

    def apply(self, db):
        return db.removeElement(self._xpath)


class ElementClear(WriteItem):
    def __init__(self, xpath, label):
        super().__init__(xpath)

    def apply(self, db):
        return db.clearElement(self._xpath)


class FunctionCall(WriteItem):
    def __init__(self, function, args, label=None):
        super().__init__(None, label)
        self._function = function
        self._args = args

    def apply(self, db):
        return getattr(db, self._function)(*self._args)


class DBWriterError:
    def __init__(self, name, error, message=None):
        self._name = name
        self._error = error
        self._message = message

    def toMessage(self):
        if self._error == DBError.OUT_OF_RANGE:
            return QCoreApplication.translate('CoreDBWriter', '{0} is out of range.').format(self._name)
        elif self._error == DBError.INTEGER_ONLY:
            return QCoreApplication.translate('CoreDBWriter', '{0} must be a integer.').format(self._name)
        elif self._error == DBError.FLOAT_ONLY:
            return QCoreApplication.translate('CoreDBWriter', '{0} must be a float.').format(self._name)
        elif self._error == DBError.REFERENCED:
            return QCoreApplication.translate('CoreDBWriter', '{0} is referenced by other configurations.').format(self._name)
        else:
            return QCoreApplication.translate('CoreDBWriter', '{0} is invalid. {1}').format(self._name, self._error)


class CoreDBWriter:
    def __init__(self):
        self._items = []
        self._errors = None

        self._db = CoreDB()

    def append(self, xpath, value, label):
        self._items.append(ValueSet(xpath, value, label))

    def setAttribute(self, xpath, name, value):
        self._items.append(AttributeSet(xpath, name, value))

    def addElement(self, xpath, element, label=None):
        self._items.append(ElementAdd(xpath, element, label))

    def removeElement(self, xpath):
        self._items.append(ElementRemove(xpath))

    def clearElement(self, xpath, label=None):
        self._items.append(ElementClear(xpath, label))

    def callFunction(self, func, args, label=None):
        self._items.append(FunctionCall(func, args, label))

    def write(self):
        self._errors = []
        with self._db:
            for i in self._items:
                try:
                    i.apply(self._db)
                except ValueException as ex:
                    error, message = ex.args
                    self._errors.append(DBWriterError(i.label, error, message))

        return len(self._errors)

    def firstError(self):
        return self._errors[0]

