#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QCoreApplication
from lxml import etree

ns = 'http://www.baramcfd.org/baram'
nsmap = {'': ns}


class DBError(Enum):
    OUT_OF_RANGE    = auto()
    INTEGER_ONLY    = auto()
    FLOAT_ONLY      = auto()
    REFERENCED      = auto()
    EMPTY           = auto()


class ValueException(Exception):
    def __init__(self, error: DBError, note):
        super().__init__(error, note)


def getElement(parent, xpath):
    return parent.find(xpath, namespaces=nsmap)


def getElements(parent, xpath):
    return parent.findall(xpath, namespaces=nsmap)


def removeElement(parent, xpath):
    element = getElement(parent, xpath)
    element.getparent().remove(element)


def getText(parent, xpath):
    return getElement(parent, xpath).text


def setText(parent, xpath, value):
    getElement(parent, xpath).text = value


def getAttribute(element, name):
    return element.get(name)


def createElement(xml):
    return etree.fromstring(xml)


def dbErrorToMessage(exception: ValueException):
    error, name = exception.args
    if error == DBError.OUT_OF_RANGE:
        return QCoreApplication.translate('CoreDBError', '{0} is out of range.').format(name)
    elif error == DBError.INTEGER_ONLY:
        return QCoreApplication.translate('CoreDBError', '{0} must be a integer.').format(name)
    elif error == DBError.FLOAT_ONLY:
        return QCoreApplication.translate('CoreDBError', '{0} must be a float.').format(name)
    elif error == DBError.REFERENCED:
        return QCoreApplication.translate('CoreDBError', '{0} is referenced by other configurations.').format(name)
    else:
        return QCoreApplication.translate('CoreDBError', '{} is invalid. {1}').format(name, error)
