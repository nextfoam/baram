#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto


class ErrorType(Enum):
    EmptyError = auto()
    EnumError = auto()
    TypeError = auto()


class ConfigError(ValueError):
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


class PrimaryType:
    def __init__(self):
        self._required = True
        self._default = None

    def setDefault(self, default):
        self._default = str(self.validate(default))
        return self

    def default(self):
        return self._default

    def validate(self, value, name=None):
        value = str(value).strip()
        if value is None or value == '':
            raise ConfigError(ErrorType.EmptyError, 'Empty value is not allowed', name)

        return value


class EnumType(PrimaryType):
    def __init__(self, *enum):
        super().__init__()
        self._enum = enum
        self._default = enum[0]

    def validate(self, value, name=None):
        value = super().validate(value)
        if value not in self._enum:
            raise ConfigError(ErrorType.EnumError, f'Only {self._enum} are allowed.', name)

        return value


class FloatType(PrimaryType):
    def __init__(self):
        super().__init__()
        self._default = 0

    def validate(self, value, name=None):
        value = super().validate(value)
        try:
            float(value)
        except Exception as e:
            raise ConfigError(ErrorType.TypeError, repr(e), name)
        return value


class Schema:
    def __init__(self, schema):
        self._schema = schema

    def rawData(self):
        return self._schema

    def generateData(self):
        return self._generateData(self._schema)

    def validateData(self, data):
        return self._validateData(data, self._schema)

    def _generateData(self, schema):
        configuration = {}
        for key in schema:
            if isinstance(schema[key], dict):
                configuration[key] = self._generateData(schema[key])
            else:
                configuration[key] = schema[key].default()

        return configuration

    def _validateData(self, data, schema, path=''):
        configuration = {}
        for key in schema:
            path = f'{path}/{key}'
            if isinstance(schema[key], dict):
                configuration[key] = self._validateData(data[key], schema[key], path)
            else:
                try:
                    configuration[key] = schema[key].validate(data[key])
                except ConfigError as ce:
                    ce.setPath(path)
                    raise ce
                except KeyError as ke:
                    raise ConfigError(ErrorType.EmptyError, repr(ke), None, path)

        return configuration
