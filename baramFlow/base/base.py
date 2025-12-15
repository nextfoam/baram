#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

from baramFlow.coredb.libdb import nsmap
from baramFlow.base.constants import Function1Type


class BatchableNumber:
    def __init__(self, text, default=None):
        self._text = text
        self._default = default

        assert not self.isParameter() or self._default is not None

    @property
    def text(self):
        return self._text

    def isParameter(self):
        return self._text.startswith('$')

    def parameter(self):
        return self._text[1:] if self.isParameter() else None

    def number(self):
        return self._default

    @staticmethod
    def fromElement(e):
        if parameter := e.get('batchParameter'):
            return BatchableNumber('$' + parameter, e.text)

        return BatchableNumber(e.text)

    def toXML(self, name):
        attr = f' batchParameter="{self.parameter()}"' if self.isParameter() else ''
        return f'<{name}{attr}>{self._default if self.isParameter() else self._text}</{name}>'


@dataclass
class Vector:
    x: BatchableNumber
    y: BatchableNumber
    z: BatchableNumber

    @staticmethod
    def new(x, y, z):
        return Vector(x=BatchableNumber(x), y=BatchableNumber(y), z=BatchableNumber(z))

    @staticmethod
    def fromElement(e):
        return Vector(x=BatchableNumber.fromElement(e.find('x', namespaces=nsmap)),
                      y=BatchableNumber.fromElement(e.find('y', namespaces=nsmap)),
                      z=BatchableNumber.fromElement(e.find('z', namespaces=nsmap)))

    def toXML(self):
        return f"{self.x.toXML('x')}{self.y.toXML('y')}{self.z.toXML('z')}"


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


@dataclass
class Function1Scalar:
    type: Function1Type = Function1Type.CONSTANT
    constant: BatchableNumber = field(default_factory=lambda: BatchableNumber('100'))
    table: list = None

    @staticmethod
    def fromElement(e):
        table = []
        if (element := e.find('table', namespaces=nsmap)) is not None:
            for row in element.findall('row', namespaces=nsmap):
                table.append(Function1ScalarRow.fromElement(row))

        return Function1Scalar(type=Function1Type(e.find('type', namespaces=nsmap).text),
                               constant=BatchableNumber.fromElement(e.find('constant', namespaces=nsmap)),
                               table=table)

    def toXML(self):
        rows = ''
        for row in self.table:
            rows += f'<row>{row.toXML()}</row>'

        return f'''
            <type>{self.type.value}</type>
            <constant>{self.constant.text}</constant>
            <table>{rows}</table>
        '''


@dataclass
class Function1Vector:
    type: Function1Type = Function1Type.CONSTANT
    constant: Vector = field(default_factory=lambda: Vector.new('1', '1', '1'))
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

    def toXML(self):
        rows = ''
        for row in self.table:
            rows += f'<row>{row.toXML()}</row>'

        return f'''
            <type>{self.type.value}</type>
            <constant>{self.constant.toXML()}</constant>
            <table>{rows}</table>
        '''
