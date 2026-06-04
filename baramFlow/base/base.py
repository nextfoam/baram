#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID
from xml.etree.ElementTree import Element

import pandas as pd
from PySide6.QtCore import QCoreApplication

from libbaram.pfloat import PFloat

from baramFlow.base.constants import Function1Type
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.libdb import E

UUID_ZERO = UUID('00000000-0000-0000-0000-000000000000')


class DirectionSpecificationMethod(Enum):
    DIRECT = 'direct'
    AOA_AOS = 'AoA_AoS'


DirectionSpecificationMethodTexts = {
    DirectionSpecificationMethod.DIRECT:    QCoreApplication.translate('base', 'Direct'),
    DirectionSpecificationMethod.AOA_AOS:   QCoreApplication.translate('base', 'AOA and AOS')
}


@dataclass
class Vector:
    x: PFloat
    y: PFloat
    z: PFloat

    @staticmethod
    def zero():
        return Vector(PFloat('0'), PFloat('0'), PFloat('0'))

    @staticmethod
    def xUnit():
        return Vector(PFloat('1'), PFloat('0'), PFloat('0'))

    @staticmethod
    def yUnit():
        return Vector(PFloat('0'), PFloat('1'), PFloat('0'))

    @staticmethod
    def zUnit():
        return Vector(PFloat('0'), PFloat('0'), PFloat('1'))

    @staticmethod
    def fromElement(e):
        return Vector(x=PFloat.fromElement(e.find('x', namespaces=nsmap)),
                      y=PFloat.fromElement(e.find('y', namespaces=nsmap)),
                      z=PFloat.fromElement(e.find('z', namespaces=nsmap)))

    def toElement(self, tag):
        return E(tag,
                 self.x.toElement('x'),
                 self.y.toElement('y'),
                 self.z.toElement('z'))

    def toFloatList(self):
        return [float(self.x), float(self.y), float(self.z)]

    def isXAligned(self):
        return float(self.y) == 0 and float(self.z) == 0

    def isYAligned(self):
        return float(self.x) == 0 and float(self.z) == 0

    def isZAligned(self):
        return float(self.x) == 0 and float(self.y) == 0

    def magnitude(self):
        return math.sqrt(float(self.x) ** 2 + float(self.y) ** 2 + float(self.z) ** 2)

    def __str__(self):
        return f'({self.x}, {self.y}, {self.z})'


@dataclass
class Function1ScalarRow:
    t: str
    v: str

    @staticmethod
    def fromElement(e):
        return Function1ScalarRow(t=e.find('t', namespaces=nsmap).text,
                                  v=e.find('v', namespaces=nsmap).text)

    def toXML(self):
        return f'<t>{self.t}</t><v>{self.v}</v>'

    def toElement(self, tag: str):
        return E(tag,
                 E('t', self.t),
                 E('v', self.v))


@dataclass
class Function1VectorRow:
    t: str
    x: str
    y: str
    z: str

    @staticmethod
    def fromElement(e):
        return Function1VectorRow(t=e.find('t', namespaces=nsmap).text,
                                  x=e.find('x', namespaces=nsmap).text,
                                  y=e.find('y', namespaces=nsmap).text,
                                  z=e.find('z', namespaces=nsmap).text)

    def toXML(self):
        return f'<t>{self.t}</t><x>{self.x}</x><y>{self.y}</y><z>{self.z}</z>'

    def toElement(self, tag:str):
        return E(tag,
                 E('t', self.t),
                 E('x', self.x),
                 E('y', self.y),
                 E('z', self.z))


@dataclass(kw_only=True)
class Function1Data:
    type: Function1Type         = Function1Type.CONSTANT
    constant: PFloat | Vector
    table: list


@dataclass
class Function1Scalar(Function1Data):
    constant: PFloat                = field(default_factory=lambda: PFloat('100'))
    table: list[Function1ScalarRow] = field(default_factory=list)

    @staticmethod
    def fromElement(e):
        table = []
        if (element := e.find('table', namespaces=nsmap)) is not None:
            for row in element.findall('row', namespaces=nsmap):
                table.append(Function1ScalarRow.fromElement(row))

        return Function1Scalar(type=Function1Type(e.find('type', namespaces=nsmap).text),
                               constant=PFloat.fromElement(e.find('constant', namespaces=nsmap)),
                               table=table)

    def toElement(self, tag: str):
        tableElement = E('table')
        tableElement.extend([row.toElement('row') for row in self.table])
        return E(tag,
                 self.type.toElement('type'),
                 self.constant.toElement('constant'),
                 tableElement)


@dataclass
class Function1Vector(Function1Data):
    constant: Vector                = field(default_factory=Vector.xUnit)
    table: list[Function1VectorRow] = field(default_factory=lambda: [])

    @staticmethod
    def fromElement(e):
        table = []
        if (element := e.find('table', namespaces=nsmap)) is not None:
            for row in element.findall('row', namespaces=nsmap):
                table.append(Function1VectorRow.fromElement(row))

        return Function1Vector(type=Function1Type(e.find('type', namespaces=nsmap).text),
                               constant=Vector.fromElement(e.find('constant', namespaces=nsmap)),
                               table=table)

    def toElement(self, tag: str):
        tableElement = E('table')
        tableElement.extend([row.toElement('row') for row in self.table])
        return E(tag,
                 self.type.toElement('type'),
                 self.constant.toElement('constant'),
                 tableElement)


class SimpleSheetData:
    columns = None

    def __init__(self, data: list[list[float]]):
        self._data = data

    @classmethod
    def default(cls):
        return cls([[0 for i in range(len(cls.columns))]])

    def data(self):
        return self._data

    def dataFrame(self):
        return pd.DataFrame(self._data)

    def columnDataString(self, index):
        return ' '.join([str(self._data[row][index]) for row in range(len(self._data))])

    def columnDataElement(self, index):
        return E(self.columns[index],
                 self.columnDataString(index))

    @classmethod
    def fromElement(cls, e):
        data = [e.find(c, namespaces=nsmap).text.split() for c in cls.columns]

        return cls(
            [[float(data[column][row]) for column in range(len(data))] for row in range(len(data[0]))])

    def toElement(self, tag: str):
        return E(tag,
                 *[self.columnDataElement(i) for i in range(len(self.columns))])


class TemporalScalarList(SimpleSheetData):
    columns = ['t', 'v']


class TemporalVectorList(SimpleSheetData):
    columns = ['t', 'x', 'y', 'z']


class SpatialScalarList(SimpleSheetData):
    columns = ['x', 'y', 'z', 'v']


class SpatialVectorList(SimpleSheetData):
    columns = ['x', 'y', 'z', 'vx', 'vy', 'vz']


class TrackedData:
    def __init__(self, init=None):
        self._initData = init
        self._data = init

    def data(self):
        return self._data

    def setData(self, data):
        self._data = data

    def isModified(self):
        return self._initData != self._data

    def isNone(self):
        return self._data is None


@dataclass
class NumberList:
    values: list[str] = field(default_factory=lambda: [])

    def isEmpty(self):
        return len(self.values) == 0

    @staticmethod
    def zeros(count: int = 1):
        return NumberList(['0'] * count)

    @staticmethod
    def fromElement(e: Element):
        if e.text is None:
            return NumberList()

        return NumberList(values=e.text.split())

    def toElement(self, tag):
        return E(tag, ' '.join(self.values))

