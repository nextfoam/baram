#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from uuid import UUID

from PySide6.QtCore import QCoreApplication
from lxml import etree

from lxml.builder import ElementMaker


ns = 'http://www.baramcfd.org/baram'
nsmap = {'': ns}


class DBError(Enum):
    OUT_OF_RANGE    = auto()
    INTEGER_ONLY    = auto()
    FLOAT_ONLY      = auto()
    REFERENCED      = auto()
    EMPTY           = auto()


class ValueException(Exception):
    def __init__(self, error: DBError, xpath, note):
        super().__init__(error, note or xpath)


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


def xmlToBool(text):
    assert text == 'true' or text == 'false'
    return text == 'true'


def boolToXml(value: bool) -> str:
    return 'true' if value else 'false'


def xmlToStr(text):
    return '' if text is None else text


def handle_bool(builder, value: bool) -> str:
    return boolToXml(value)


def handleEnum(builder, value: Enum) -> str:
    return value.value


def handleUUID(builder, value) -> str:
    return str(value)


E = ElementMaker(namespace=ns, typemap={
    bool: handle_bool,
    Enum: handleEnum,
    UUID: handleUUID
})


class ElementEnum(Enum):
    def toElement(self, tag:str):
        return E(tag, self.value)


