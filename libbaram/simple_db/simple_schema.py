#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import QObject


class ErrorType(Enum):
    EmptyError = auto()
    EnumError = auto()
    TypeError = auto()
    RangeError = auto()
    SizeError = auto()


def generateData(schema):
    configuration = {}
    for key in schema:
        if isinstance(schema[key], dict):
            configuration[key] = generateData(schema[key])
        elif schema[key].isRequired():
            configuration[key] = schema[key].default()
        else:
            configuration[key] = None

    return configuration


def validateData(data, schema, path='', fillWithDefault=False):
    configuration = {}
    for key in schema:
        subPath = f'{path}/{key}'
        if isinstance(schema[key], dict):
            if key in data:
                configuration[key] = validateData(data[key], schema[key], subPath, fillWithDefault=fillWithDefault)
            elif fillWithDefault:
                configuration[key] = validateData({}, schema[key], subPath, fillWithDefault=fillWithDefault)
            else:
                raise ValidationError(ErrorType.EmptyError, 'Empty value is not allowed', key, subPath)
        elif isinstance(schema[key], SchemaList):
            if key in data:
                configuration[key] = schema[key].validate(data[key], subPath, fillWithDefault=fillWithDefault)
            else:
                configuration[key] = {}
        else:
            try:
                if key in data:
                    configuration[key] = schema[key].validate(data[key], key)
                elif not schema[key].isRequired():
                    configuration[key] = None
                elif fillWithDefault:
                    configuration[key] = schema[key].default()
                else:
                    raise ValidationError(ErrorType.EmptyError, 'Empty value is not allowed', key, subPath)
            except ValidationError as ce:
                ce.setPath(subPath)
                raise ce
            except KeyError as ke:
                raise ValidationError(ErrorType.EmptyError, repr(ke), None, subPath)

    return configuration


class ValidationError(ValueError):
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
        return f'{self._path if self._name is None else self._name} - {self._message}'


class PrimitiveType(QObject):
    def __init__(self):
        super().__init__()

        self._required = True
        self._default = None

    def setDefault(self, default):
        self._default = self.validate(default)

        return self

    def setOptional(self):
        self._required = False

        return self

    def default(self):
        return self._default

    def isRequired(self):
        return self._required

    def validate(self, value, name=None):
        validated = None if value is None else str(value).strip()
        if self._required and (validated is None or validated == ''):
            raise ValidationError(ErrorType.EmptyError, self.tr('Empty value is not allowed'), name)

        return validated


class EnumType(PrimitiveType):
    def __init__(self, enumClass):
        super().__init__()
        self._cls = enumClass
        self._values = {e.value: e for e in enumClass if isinstance(e.value, str) or isinstance(e.value, int)}
        self.setDefault(list(enumClass)[0])

    def validate(self, value, name=None):
        if not self._required and value is None:
            return value

        if value in self._values:
            return value if isinstance(value, str) else self._cls(value).name

        if isinstance(value, self._cls):
            return value.value if isinstance(value.value, str) else value.name

        if value in self._cls.__members__:
            return value

        raise ValidationError(ErrorType.EnumError, self.tr('Only {} are allowed.').format(self._cls), name)

    def toEnum(self, value):
        return self._values.get(value) or self._cls[value]


class FloatType(PrimitiveType):
    def __init__(self):
        super().__init__()
        self._default = '0'
        self._lowLimit = None
        self._lowLimitInclusive = True
        self._highLimit = None
        self._highLimitInclusive = True

    def setLowLimit(self, limit, inclusive=True):
        self._lowLimit = limit
        self._lowLimitInclusive = inclusive

        return self

    def setHighLimit(self, limit, inclusive=True):
        self._highLimit = limit
        self._highLimitInclusive = inclusive

        return self

    def setRange(self, low, high):
        self._lowLimit = low
        self._highLimit = high
        self._lowLimitInclusive = True
        self._highLimitInclusive = True

        return self

    def validate(self, value, name=None):
        def rangeToText():
            if self._highLimit is None:
                if self._lowLimitInclusive:
                    return f' (value ≥ {self._lowLimit})'
                else:
                    return f' (value > {self._lowLimit})'

            lowLimit = ' ('
            if self._lowLimit is not None:
                if self._lowLimitInclusive:
                    lowLimit =  f' ({self._lowLimit} ≤ '
                else:
                    lowLimit =  f' ({self._lowLimit} < '

            if self._highLimitInclusive:
                return f'{lowLimit}value ≤ {self._highLimit})'
            else:
                return f'{lowLimit}value < {self._highLimit})'

        value = super().validate(value, name)

        if value is None or value == '':
            return None

        try:
            v = float(value)
        except Exception as e:
            raise ValidationError(ErrorType.TypeError, repr(e), name)

        if self._lowLimit is not None:
            if v < self._lowLimit or (v == self._lowLimit and not self._lowLimitInclusive):
                raise ValidationError(ErrorType.RangeError, self.tr('Out of Range') + rangeToText(), name)
        if self._highLimit is not None:
            if v > self._highLimit or (v == self._highLimit and not self._highLimitInclusive):
                raise ValidationError(ErrorType.RangeError, self.tr('Out of Range') + rangeToText(), name)

        return value


class IntType(FloatType):
    def __init__(self):
        super().__init__()
        self._default = '0'

    def validate(self, value, name=None):
        value = super().validate(value, name)

        if value is None:
            return None

        try:
            f = float(value)
            if int(f) != f:
                raise ValidationError(ErrorType.TypeError, self.tr('Only integers are allowed'), name)
        except Exception as e:
            raise ValidationError(ErrorType.TypeError, repr(e), name)

        return value


class TextType(PrimitiveType):
    def __init__(self):
        super().__init__()
        self._default = ''


class BoolType(PrimitiveType):
    def __init__(self, default: bool):
        super().__init__()
        self._default = default

    def validate(self, value, name=None):
        return True if value else False


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
            data[key] = validateData(value[key], self._schema, name, fillWithDefault=fillWithDefault)

        return data

    def validateElement(self, db, fullCheck=False):
        if fullCheck:
            return validateData(db.data(), self._schema)

        return db.data()

    def newElement(self):
        return generateData(self._schema)

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
                raise ValidationError(ErrorType.TypeError, repr(ke), self.tr('Key of List'))

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


class SimpleArray(PrimitiveType):
    def __init__(self, type_, size=0):
        super().__init__()

        self._type: PrimitiveType = type_
        self._value = []
        self._size = size

    def default(self):
        return [self._type.default()] * self._size

    def validate(self, value, name=None, fillWithDefault=False):
        if not isinstance(value, list):
            raise ValidationError(ErrorType.TypeError, self.tr('A list is required'), name)

        if self._size and len(value) != self._size:
            raise ValidationError(ErrorType.SizeError, self.tr('Length must be {}'.format(self._size)), name)

        validated = [None] * len(value)
        for i in range(len(value)):
            validated[i] = self._type.validate(value[i], f'{name}[{i}]')

        return validated


class SimpleSchema:
    def __init__(self, schema):
        self._schema = schema

    def schema(self):
        return self._schema

    def generateData(self):
        return generateData(self._schema)

    def validateData(self, data, fillWithDefault=False):
        return validateData(data, self._schema, fillWithDefault=fillWithDefault)
