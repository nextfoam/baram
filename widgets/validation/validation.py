#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject


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
            if edit.isVisible() and not edit.text().strip():
                return False, self.tr('{} is required.'.format(name))

        for v in self._validations:
            valid, msg = v.validate()
            if not valid:
                return False, msg

        return True, None
