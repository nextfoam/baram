#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

import yaml

from .simple_schema import SimpleSchema, SchemaList, PrimitiveType, EnumType, DBError, ErrorType


def elementToVector(element):
    if 'x' not in element or 'y' not in element or 'z' not in element:
        raise LookupError

    return [float(element['x']), float(element['y']), float(element['z'])]


def elementToList(element, schema, keys):
    if not all(field in element and isinstance(schema[field], PrimitiveType) for field in keys):
        raise LookupError

    return [element[field] for field in keys]


def _getField(pathData):
    schema, content, field = pathData
    return (schema, content) if field is None else (schema[field], content[field])


class Element:
    def __init__(self, element, scheme):
        self._data = element
        self._scheme = scheme

    def value(self, field):
        if isinstance(self._data[field], dict):
            raise LookupError

        return self._data[field]

    def vector(self, field):
        if not isinstance(self._data[field], dict):
            raise LookupError

        return elementToVector(self._data[field])

    def float(self, field):
        return float(self.value(field))

    def int(self, field):
        return int(self.value(field))

    def elements(self, field):
        if not isinstance(self._scheme[field], SchemaList):
            raise TypeError

        return {key: Element(self._data[field][key], self._scheme[field].elementSchema())
                for key in self._data[field]}

    def element(self, field):
        if not isinstance(self._data[field], dict):
            raise LookupError

        return Element(self._data[field], self._scheme[field])


class SimpleDB(SimpleSchema):
    def __init__(self, schema):
        super().__init__(schema)
        self._content = None
        self._editable = False
        self._modified = False
        self._base = ''

    def isModified(self):
        return self._modified

    def createData(self):
        self._content = self.generateData()

    def data(self):
        return self._content

    def checkout(self, path=''):
        """ Creates and returns a SimpleDB replicated with the original's subdata.

        :param path: The root path to clone.
        :return: New SimpleDB based on specific path.
        """
        subSchema = self._schema
        subDB = self._content
        if path != self._base:
            schema, content, field = self._get(path)

            if isinstance(schema, SchemaList):
                subSchema = schema.elementSchema()
            else:
                subSchema = schema[field]

            subDB = content[field]

        subData = self._newDB(subSchema)
        subData._content = copy.deepcopy(subDB)
        subData._editable = True
        subData._base = f'{self._base}/{path}' if self._base else path

        return subData

    def commit(self, data):
        """ Replaces part of the data

        :param data: SimpleDB based on the root path of the data to be replaced
        """
        if not data._base.startswith(self._base):
            raise LookupError

        if not data._modified or not data._editable:
            return

        if data._base == self._base:
            self._content = data._content
        else:
            path = data._base[len(self._base) + 1:] if self._base else data._base
            schema, content, field = self._get(path)
            content[field] = data._content

        data._modified = False
        data._editable = False
        self._modified = True

    def getValue(self, path):
        schema, content, field = self._get(path)
        if isinstance(content[field], dict):
            raise LookupError

        return content[field]

    def getValues(self, path, fields):
        schema, content, field = self._get(path)
        if not isinstance(content[field], dict):
            raise LookupError

        return elementToList(content[field], schema[field], fields)

    def getFloat(self, path):
        value = self.getValue(path)

        return None if value is None else float(value)

    def getVector(self, path):
        schema, content, field = self._get(path)
        if not isinstance(content[field], dict):
            raise LookupError

        return elementToList(content[field], schema[field], ['x', 'y', 'z'])

    def getEnum(self, path):
        schema, content, field = self._get(path)
        if not isinstance(schema[field], EnumType):
            raise LookupError

        return schema[field].toEnum(content[field])

    def setValue(self, path, value, name=None):
        if not self._editable:
            raise LookupError

        schema, content, field = self._get(path)
        value = schema[field].validate(value, name)
        if content[field] != value:
            content[field] = value
            self._modified = True

            return True

        return False

    def setText(self, path, text, name=None):
        if text.strip():
            self.setValue(path, text, name)
            return True

        raise DBError(ErrorType.EmptyError, 'Empty value is not allowed', name)

    def newElement(self, path):
        schema, _, = _getField(self._get(path))
        if not isinstance(schema, SchemaList):
            raise TypeError

        db = self._newDB(schema.elementSchema(), True)
        db.createData()

        return db

    def addElement(self, path, newdb, key=None):
        if not self._editable:
            raise LookupError

        schema, content = _getField(self._get(path))

        if not isinstance(schema, SchemaList):
            raise TypeError

        key = schema.key(key, content)
        if key in content:
            raise KeyError

        if schema.elementSchema() == newdb._schema:
            content[key] = schema.validateElement(newdb)
        else:
            raise TypeError

        newdb._editable = False
        self._modified = True

        return key

    def addNewElement(self, path, key=None):
        if not self._editable:
            raise LookupError

        schema, content = _getField(self._get(path))

        if not isinstance(schema, SchemaList):
            raise TypeError

        key = schema.key(key, content)
        if key in content:
            raise KeyError

        element = self._newDB(schema.elementSchema())
        element.createData()
        content[key] = element._content

        self._modified = True

        return key, element

    def getElement(self, path, key=None):
        schema, content, field = self._get(path)
        if key:
            schema, content = _getField((schema, content, field))
            field = key

            if not field in content:
                return None

        if isinstance(schema, SchemaList):
            return Element(content[field], schema.elementSchema())
        else:
            return Element(content[field], schema[field])

    def getElements(self, path: str = None, filter_=None):
        schema, content = _getField(self._get(path))
        if not isinstance(schema, SchemaList):
            raise TypeError

        return {key: Element(content[key], schema.elementSchema())
                for key in content if filter_ is None or filter_(key, content[key])}

    def findElement(self, path=None, filter_=None):
        elements = self.getElements(path, filter_)
        if len(elements) == 1:
            return list(elements.items())[0]

        return None, None

    def getKeys(self, path: str = None, filter_=None):
        schema, content = _getField(self._get(path))
        if not isinstance(schema, SchemaList):
            raise TypeError

        return [key for key in content if filter_ is None or filter_(key, content[key])]

    def removeElement(self, path, key):
        if not self._editable:
            raise LookupError

        schema, content = _getField(self._get(path))

        if not isinstance(schema, SchemaList):
            raise TypeError

        if key not in content:
            raise KeyError

        del content[key]

        self._modified = True

    def removeElements(self, path, keys):
        if not self._editable:
            raise LookupError

        schema, content = _getField(self._get(path))

        if not isinstance(schema, SchemaList):
            raise TypeError

        if any(key not in content for key in keys):
            raise KeyError

        for key in keys:
            del content[key]

        self._modified = True

    def removeElementsByFilter(self, path, function):
        if not self._editable:
            raise LookupError

        schema, content = _getField(self._get(path))

        if not isinstance(schema, SchemaList):
            raise TypeError

        for key in [e[0] for e in content.items() if function(e[0], e[1])]:
            del content[key]

        self._modified = True

    def removeAllElements(self, path):
        if not self._editable:
            raise LookupError

        schema, content, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        content[field] = {}

        self._modified = True

    def updateElements(self, path, field, value, filter_=None, name=None):
        schema, content = _getField(self._get(path))
        if not isinstance(schema, SchemaList):
            raise TypeError

        value = schema.elementSchema()[field].validate(value, name)
        keys = [key for key in content if filter_ is None or filter_(key, content[key])]
        for key in keys:
            if content[key][field] != value:
                content[key][field] = value
                self._modified = True

        return keys

    def hasElement(self, path, key):
        schema, content = _getField(self._get(path))

        if not isinstance(schema, SchemaList):
            raise TypeError

        return str(key) in content

    def elementCount(self, path=None, filter_=None):
        if filter_ is not None:
            return len(self.getKeys(path, filter_))

        schema, content = _getField(self._get(path))
        if not isinstance(schema, SchemaList):
            raise TypeError

        return len(content)

    def getUniqueValue(self, path, field, value):
        return f'{value}{self.getUniqueSeq(path, field, value)}'

    def getUniqueSeq(self, path, field, value, start=''):
        if start:
            seq = int(start)
            result = f'{value}{seq}'
        else:
            seq = 0
            result = value

        while self.getElements(path, lambda i, e: e[field] == result):
            seq += 1
            result = f'{value}{seq}'

        return str(seq) if seq or start else ''

    def keyExists(self, path, key):
        schema, content = _getField(self._get(path))
        if not isinstance(schema, SchemaList):
            raise TypeError

        return key in content

    def toYaml(self):
        return yaml.dump(self._content)

    def loadYaml(self, data, fillWithDefault=False):
        self._content = self.validateData(yaml.full_load(data), fillWithDefault=fillWithDefault)

    def _get(self, path):
        if path is None:
            return self._schema, self._content, None

        fields = path.split('/')
        schema = self._schema
        content = self._content

        depth = len(fields) - 1
        for i in range(depth):
            if isinstance(schema, SchemaList):
                schema = schema.elementSchema()
                content = content[fields[i]]
            else:
                schema = schema[fields[i]]
                content = content[fields[i]]

        return schema, content, fields[depth]

    def _newDB(self, schema, editable=False):
        db = SimpleDB(schema)
        db._editable = editable

        return db
