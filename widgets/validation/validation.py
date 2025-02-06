#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject


def isEditable(edit):
    return edit.isVisible() and edit.isEnabled()


class Validator(QObject):
    def __init__(self):
        super().__init__()

    def validate(self):
        raise NotImplementedError


class FormValidator(Validator):
    def __init__(self):
        super().__init__()

        self._required = []
        self._validations = []

    def addRequiredValidation(self, edit, name):
        self._required.append((edit, name))

    def addCustomValidation(self, validator):
        self._validations.append(validator)

    def validate(self):
        for edit, name in self._required:
            if isEditable(edit) and not edit.text().strip():
                return False, self.tr('{} is required.'.format(name))

        for v in self._validations:
            valid, msg = v.validate()
            if not valid:
                return False, msg

        return True, None


class FloatValidator(Validator):
    def __init__(self, edit, name):
        super().__init__()

        self._edit = edit
        self._name = name

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

    def validate(self):
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

        try:
            value = float(self._edit.text())

            if self._lowLimit is not None:
                if value < self._lowLimit or (value == self._lowLimit and not self._lowLimitInclusive):
                    return False, self.tr('Out of Range: ') + rangeToText()

            if self._highLimit is not None:
                if value > self._highLimit or (value == self._highLimit and not self._highLimitInclusive):
                    return False, self.tr('Out of Range: ') + rangeToText()

            return True, value
        except ValueError:
            return False, self.tr('{} must be a number'.format(self._name))


class NotGreaterValidator(FloatValidator):
    def __init__(self, myEdit, otherEdit, myName, otherName):
        super().__init__(myEdit, myName)

        self._other = otherEdit
        self._otherName = otherName

    def validate(self):
        valid, me = super().validate()
        if not valid:
            return valid, me

        valid, other = FloatValidator(self._other, self._otherName).validate()
        if not valid:
            return valid, other

        if me > other:
            return False, self.tr('{} cannot be greater than {}'.format(self._name, self._otherName))

        return True, None
