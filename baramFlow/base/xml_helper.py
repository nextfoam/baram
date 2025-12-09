#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum

from baramFlow.coredb.batch_parameter_db import BatchParametersDB


@dataclass
class Vector:
    x: str
    y: str
    z: str


def toXML(data):
    if isinstance(data, Enum):
        return data.value

    if isinstance(data, bool):
        return 'true' if data else 'bool'

    if isinstance(data, Vector):
        return f'''
            <x>{data.x}</x>
            <y>{data.y}</y>
            <z>{data.z}</z>
        '''

def toBatchParamXML(name, data: str):
    if data.startswith('$'):
        parameter = data[1:]
        attr = f' batchParameter="{parameter}'
        value = BatchParametersDB.defaultValue(parameter)
    else:
        attr = ''
        value = data

    return f'<{name}{attr}>{value}</{name}>'
