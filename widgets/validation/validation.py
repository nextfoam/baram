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

    def validate(self):
        try:
            return True, float(self._edit.text())
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
