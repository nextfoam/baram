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
            schema, db, field = self._get(path)

            if isinstance(schema, SchemaList):
                subSchema = schema.elementSchema()
            else:
                subSchema = schema[field]

            subDB = db[field]

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
            schema, db, field = self._get(path)
            db[field] = data._content

        data._modified = False
        data._editable = False
        self._modified = True

    def getValue(self, path):
        schema, db, field = self._get(path)
        if isinstance(db[field], dict):
            raise LookupError

        return db[field]

    def getValues(self, path, fields):
        schema, db, field = self._get(path)
        if not isinstance(db[field], dict):
            raise LookupError

        return elementToList(db[field], schema[field], fields)

    def getFloat(self, path):
        value = self.getValue(path)

        return None if value is None else float(value)

    def getVector(self, path):
        schema, db, field = self._get(path)
        if not isinstance(db[field], dict):
            raise LookupError

        return elementToList(db[field], schema[field], ['x', 'y', 'z'])

    def getEnum(self, path):
        schema, db, field = self._get(path)
        if not isinstance(schema[field], EnumType):
            raise LookupError

        return schema[field].valueToEnum(db[field])

    def getEnumValue(self, path):
        schema, db, field = self._get(path)
        if not isinstance(schema[field], EnumType):
            raise LookupError

        return schema[field].enumValue(db[field])

    def setValue(self, path, value, name=None):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)
        value = schema[field].validate(value, name)
        if db[field] != value:
            db[field] = value
            self._modified = True

            return True

        return False

    def setText(self, path, text, name=None):
        if text.strip():
            self.setValue(path, text, name)
            return True

        raise DBError(ErrorType.EmptyError, 'Empty value is not allowed', name)

    def newElement(self, path):
        schema, _, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        db = self._newDB(schema.elementSchema(), True)
        db.createData()

        return db

    def addElement(self, path, newdb, key=None):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        key = schema.key(key, db[field])
        if key in db[field]:
            raise KeyError

        if schema.elementSchema() == newdb._schema:
            db[field][key] = schema.validateElement(newdb)
        else:
            raise TypeError

        newdb._editable = False
        self._modified = True

        return key

    def addNewElement(self, path, key=None):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        key = schema.key(key, db[field])
        if key in db[field]:
            raise KeyError

        element = self._newDB(schema.elementSchema())
        element.createData()
        db[field][key] = element._content

        self._modified = True

        return key, element

    def getElement(self, path, key, columns=None):
        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        key = str(key)
        if key not in db[field]:
            raise LookupError

        if columns is None:
            return copy.deepcopy(db[field][key])

        return {k: copy.deepcopy(db[field][key][k]) for k in columns}

    def getElements(self, path: str = None, filter_=None, columns=None):
        if not path:
            schema = self._schema
            db = self._content
        else:
            schema, db, field = self._get(path)
            schema = schema[field]
            db = db[field]

        if not isinstance(schema, SchemaList):
            raise TypeError

        if columns is None:
            return copy.deepcopy(
                {key: db[key] for key in db if filter_ is None or filter_(key, db[key])})

        return {
            key: {k: copy.deepcopy(db[key][k]) for k in columns}
            for key in db if filter_ is None or filter_(key, db[key])}

    def getKeys(self, path: str = None, filter_=None):
        if not path:
            schema = self._schema
            db = self._content
        else:
            schema, db, field = self._get(path)
            schema = schema[field]
            db = db[field]

        if not isinstance(schema, SchemaList):
            raise TypeError

        return [key for key in db if filter_ is None or filter_(key, db[key])]

    def removeElement(self, path, key):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        if key not in db[field]:
            raise KeyError

        del db[field][key]

        self._modified = True

    def removeElements(self, path, keys):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        if any(key not in db[field] for key in keys):
            raise KeyError

        for key in keys:
            del db[field][key]

        self._modified = True

    def removeElementsByFilter(self, path, function):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        for key in [e[0] for e in db[field].items() if function(e[0], e[1])]:
            del db[field][key]

        self._modified = True

    def removeAllElements(self, path):
        if not self._editable:
            raise LookupError

        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        db[field] = {}

        self._modified = True

    def updateElements(self, path, field, value, filter_=None, name=None):
        if not path:
            schema = self._schema
            db = self._content
        else:
            schema, db, item = self._get(path)
            schema = schema[item]
            db = db[item]

        if not isinstance(schema, SchemaList):
            raise TypeError

        value = schema.elementSchema()[field].validate(value, name)
        keys = [key for key in db if filter_ is None or filter_(key, db[key])]
        for key in keys:
            if db[key][field] != value:
                db[key][field] = value
                self._modified = True

        return keys

    def hasElement(self, path, key):
        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        return str(key) in db[field]

    def elementCount(self, path=None, filter_=None):
        if filter_ is not None:
            return len(self.getKeys(path, filter_))

        if not path:
            schema = self._schema
            db = self._content
        else:
            schema, db, field = self._get(path)
            schema = schema[field]
            db = db[field]

        if not isinstance(schema, SchemaList):
            raise TypeError

        return len(db)

    def getUniqueValue(self, path, field, value):
        return f'{value}{self.getUniqueSeq(path, field, value)}'

    def getUniqueSeq(self, path, field, value, start=''):
        if start:
            seq = int(start)
            result = f'{value}{seq}'
        else:
            seq = 0
            result = value

        while self.getElements(path, lambda i, e: e[field] == result, []):
            seq += 1
            result = f'{value}{seq}'

        return str(seq) if seq or start else ''

    def keyExists(self, path, key):
        schema, db, field = self._get(path)

        schema = schema[field]
        if not isinstance(schema, SchemaList):
            raise TypeError

        return key in db[field]

    def toYaml(self):
        return yaml.dump(self._content)

    def loadYaml(self, data, fillWithDefault=False):
        self._content = self.validateData(yaml.full_load(data), fillWithDefault=fillWithDefault)

    def _get(self, path):
        fields = path.split('/')
        schema = self._schema
        data = self._content

        depth = len(fields) - 1
        for i in range(depth):
            if isinstance(schema, SchemaList):
                schema = schema.elementSchema()
                data = data[fields[i]]
            else:
                schema = schema[fields[i]]
                data = data[fields[i]]

        return schema, data, fields[depth]

    def _newDB(self, schema, editable=False):
        db = SimpleDB(schema)
        db._editable = editable

        return db
