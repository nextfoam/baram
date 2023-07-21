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
        elif schema[key].isRequired():
            configuration[key] = schema[key].default()
        else:
            configuration[key] = ''

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


class PrimitiveType:
    def __init__(self):
        self._required = True
        self._default = None

    def setDefault(self, default):
        self._default = str(self.validate(default))

        return self

    def setOptional(self):
        self._required = False

        return self

    def default(self):
        return self._default

    def isRequired(self):
        return self._required

    def validate(self, value, name=None):
        value = str(value).strip()
        if self._required and (value is None or value == ''):
            raise DBError(ErrorType.EmptyError, 'Empty value is not allowed', name)

        return value


class EnumType(PrimitiveType):
    def __init__(self, enumClass):
        super().__init__()
        self._cls = enumClass
        self._values = [e.value for e in enumClass]
        self.setDefault(list(enumClass)[0])

    def validate(self, value, name=None):
        if not self._required and value == '':
            return value

        if value in self._values:
            return value if isinstance(value, str) else self._cls(value).name

        if isinstance(value, self._cls):
            return value.value if isinstance(value.value, str) else value.name

        if value in self._cls.__members__:
            return value

        raise DBError(ErrorType.EnumError, f'Only {self._cls} are allowed.', name)

    def valueToEnum(self, value):
        return self._cls(value) if isinstance(value, self._cls) else self._cls[value]

    def enumValue(self, value):
        return value if isinstance(value, self._cls) else self._cls[value].value


class FloatType(PrimitiveType):
    def __init__(self):
        super().__init__()
        self._default = '0'

    def validate(self, value, name=None):
        value = super().validate(value, name)
        try:
            if value != '':
                float(value)
        except Exception as e:
            raise DBError(ErrorType.TypeError, repr(e), name)

        return value


class IntType(PrimitiveType):
    def __init__(self):
        super().__init__()
        self._default = '0'

    def validate(self, value, name=None):
        value = super().validate(value, name)
        try:
            if value != '':
                f = float(value)
                if int(f) != f:
                    raise DBError(ErrorType.TypeError, 'Only integers allowed', name)
        except Exception as e:
            raise DBError(ErrorType.TypeError, repr(e), name)

        return value


class PositiveIntType(IntType):
    def __init__(self):
        super().__init__()
        self._default = '1'

    def validate(self, value, name=None):
        value = super().validate(value, name)
        try:
            if value != '':
                if int(value) < 1:
                    raise DBError(ErrorType.TypeError, 'Only positive integers allowed', name)
        except Exception as e:
            raise DBError(ErrorType.TypeError, repr(e), name)

        return value


class TextType(PrimitiveType):
    def __init__(self):
        super().__init__()
        self._default = ''


class KeyType(PrimitiveType):
    def __init__(self):
        super().__init__()
        self._default = '0'

    def validate(self, value, name=None):
        value = super().validate(value, name)
        try:
            if value != '':
                f = float(value)
                if int(f) != f:
                    raise DBError(ErrorType.TypeError, 'Only integers allowed', name)
        except Exception as e:
            raise DBError(ErrorType.TypeError, repr(e), name)

        return value


class BoolType(PrimitiveType):
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

    def isRequired(self):
        return True

    def validate(self, value, name=None, fillWithDefault=False):
        data = {}

        for key in value:
            data[key] = validateData(value[key], self._schema.schema(), name, fillWithDefault=fillWithDefault)

        return data

    def newElement(self):
        return self._schema.generateData()

    def key(self, key, data):
        if key is None:
            raise KeyError

        return str(key)


class IntKeyList(SchemaList):
    def __init__(self, schema):
        super().__init__(schema)

    def key(self, key, data):
        if key is None:
            if data:
                key = max([int(k) for k in data.keys()]) + 1
            else:
                key = 1
        else:
            try:
                int(key)
            except KeyError as ke:
                raise DBError(ErrorType.TypeError, repr(ke), 'Key of List')

        return str(key)


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


class SimpleSchema:
    def __init__(self, schema):
        self._schema = schema

    def schema(self):
        return self._schema

    def generateData(self):
        return generateData(self._schema)

    def validateData(self, data, fillWithDefault=False):
        return validateData(data, self._schema, fillWithDefault=fillWithDefault)


class ElementSchema(SimpleSchema):
    def __init__(self, schema):
        super().__init__(schema)

    def validateElement(self, db, fullCheck=False):
        if fullCheck:
            return self.validateData(db.data())

        return db.data()
