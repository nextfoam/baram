#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baram.coredb.coredb import CoreDB, Error


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


class FunctionCall(WriteItem):
    def __init__(self, function, *args):
        super().__init__(None, 'Materials configuration update failed.')
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
        if self._error == Error.OUT_OF_RANGE:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} is out of range.')
        elif self._error == Error.INTEGER_ONLY:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} must be a integer.')
        elif self._error == Error.FLOAT_ONLY:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} must be a float.')
        elif self._error == Error.REFERENCED:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} is referenced by another.')
        else:
            return QCoreApplication.translate('CoreDBWriter', f'{self._name} is invalid. {self._error}')


class CoreDBWriter:
    def __init__(self):
        self._items = []
        self._errors = None

        self._db = CoreDB()

    def append(self, xpath, value, label):
        self._items.append(ValueSet(xpath, value, label))

    def setAttribute(self, xpath, name, value):
        self._items.append(AttributeSet(xpath, name, value))

    def removeElement(self, xpath):
        self._items.append(ElementRemove(xpath))

    def addElement(self, xpath, element, label):
        self._items.append(ElementAdd(xpath, element, label))

    def callFunction(self, func, *args):
        self._items.append(FunctionCall(func, *args))

    def write(self):
        self._errors = []
        with self._db:
            for i in self._items:
                if error := i.apply(self._db):
                    self._errors.append(DBWriterError(i.label, error))

        return len(self._errors)

    def firstError(self):
        return self._errors[0]

