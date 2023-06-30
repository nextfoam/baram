#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto


class ErrorType(Enum):
    EmptyError = auto()
    EnumError = auto()
    TypeError = auto()


def generateData(schema):
    configuration = {}
    for key in schema:
        if isinstance(schema[key], dict):
            configuration[key] = generateData(schema[key])
        else:
            configuration[key] = schema[key].default()

    return configuration


def validateData(data, schema, path='', fillWithDefault=False):
    configuration = {}
    for key in schema:
        path = f'{path}/{key}'
        if isinstance(schema[key], dict):
            if key in data:
                configuration[key] = validateData(data[key], schema[key], path, fillWithDefault=fillWithDefault)
            elif fillWithDefault:
                configuration[key] = {}
            else:
                raise DBError(ErrorType.EmptyError, 'Empty value is not allowed', key, path)
        elif isinstance(schema[key], SchemaList):
            if key in data:
                configuration[key] = schema[key].validate(data[key], path, fillWithDefault=fillWithDefault)
            else:
                configuration[key] = {}
        else:
            try:
                if key in data:
                    configuration[key] = schema[key].validate(data[key])
                elif fillWithDefault:
                    configuration[key] = schema[key].default()
                else:
                    raise DBError(ErrorType.EmptyError, 'Empty value is not allowed', key, path)
            except DBError as ce:
                ce.setPath(path)
                raise ce
            except KeyError as ke:
                raise DBError(ErrorType.EmptyError, repr(ke), None, path)

    return configuration


class DBError(ValueError):
    def __init__(self, type_, message, name=None, path=None):
        super().__init__(message)
        self._message = message
        self._type = type_
        self._name = name
        self._path = path

    @property
    def type(self):
        return self._type

    @property
    def message(self):
        return self._message

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    def setPath(self, path):
        self._path = path

    def toMessage(self):
        return f'{self._name} - {self._message}'


class SimpleType:
    def __init__(self):
        self._required = True
        self._default = None
        self._optional = False

    def setDefault(self, default):
        self._default = str(self.validate(default))

        return self

    def setOptional(self):
        self._optional = True

        return self

    def default(self):
        return self._default

    def validate(self, value, name=None):
        value = str(value).strip()
        if not self._optional and (value is None or value == ''):
            raise DBError(ErrorType.EmptyError, 'Empty value is not allowed', name)

        return value


class EnumType(SimpleType):
    def __init__(self, enumClass):
        super().__init__()
        self._cls = enumClass
        self._default = list(enumClass)[0].value
        self._values = [e.value for e in enumClass]

    def validate(self, value, name=None):
        if isinstance(value, self._cls):
            return value.value

        if value in self._values:
            return value

        raise DBError(ErrorType.EnumError, f'Only {self._cls} are allowed.', name)


class FloatType(SimpleType):
    def __init__(self):
        super().__init__()
        self._default = '0'

    def validate(self, value, name=None):
        value = super().validate(value, name)
        try:
            float(value)
        except Exception as e:
            raise DBError(ErrorType.TypeError, repr(e), name)

        return value


class IntType(SimpleType):
    def __init__(self):
        super().__init__()
        self._default = '0'

    def validate(self, value, name=None):
        value = super().validate(value, name)
        try:
            f = float(value)
            if int(f) != f:
                raise DBError(ErrorType.TypeError, 'Only integers allowed', name)
        except Exception as e:
            raise DBError(ErrorType.TypeError, repr(e), name)

        return value


class TextType(SimpleType):
    def __init__(self):
        super().__init__()
        self._default = ''


class BoolType(SimpleType):
    def __init__(self, default: bool):
        super().__init__()
        self.setDefault(default)

    def validate(self, value, name=None):
        return 'true' if value else 'false'


class SchemaList:
    def __init__(self,  schema):
        self._schema = schema

    def elementSchema(self):
        return self._schema

    def default(self):
        return {}

    def validate(self, value, name=None, fillWithDefault=False):
        data = {}

        for key in value:
            data[key] = validateData(value[key], self._schema.schema(), name, fillWithDefault=fillWithDefault)

        return data

    def newElement(self):
        return self._schema.generateData()

    def index(self, index, data):
        if index is None:
            raise KeyError

        return index


class IntKeyList(SchemaList):
    def __init__(self, schema):
        super().__init__(schema)

    def index(self, index, data):
        if index is None:
            if data:
                return max(data.keys()) + 1
            else:
                return 1

        return index


class TextKeyList(SchemaList):
    def __init__(self, schema):
        super().__init__(schema)


class SchemaComposite:
    def __init__(self, schema):
        self._schema = schema

    def schema(self):
        return self._schema


class VectorComposite(SchemaComposite):
    def __init__(self):
        super().__init__({
            'x': FloatType(),
            'y': FloatType(),
            'z': FloatType()
        })

    def setDefault(self, x, y, z):
        self._schema['x'].setDefault(x)
        self._schema['y'].setDefault(y)
        self._schema['z'].setDefault(z)

        return self


class Schema:
    def __init__(self, schema):
        self._schema = schema

    def schema(self):
        return self._schema

    def generateData(self):
        return generateData(self._schema)

    def validateData(self, data, fillWithDefault=False):
        return validateData(data, self._schema, fillWithDefault=fillWithDefault)


class ElementSchema(Schema):
    def __init__(self, schema):
        super().__init__(schema)

    def validateElement(self, db, fullCheck=False):
        if fullCheck:
            return self.validateData(db.data())

        return db.data()
