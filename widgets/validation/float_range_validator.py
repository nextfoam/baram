#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .validation import Validator


class FloatRangeValidator(Validator):
    def __init__(self, edit, name, bottom=None, top=None, bottomExclusive=False, topExclusive=False):
        super().__init__()

        self._edit = edit
        self._name = name

        self._top = top
        self._bottom = bottom
        self._bottomExclusive = bottomExclusive
        self._topExclusive = topExclusive

    def validate(self):
        text = self._edit.text().strip()
        if not text:
            return False, self.tr('{} is required.'.format(self._name))

        value = float(text)
        if self._bottom is not None:
            if self._bottomExclusive and value <= self._bottom:
                return False, self.tr('{} must be greater than {}.'.format(self._name, self._bottom))

            if not self._bottomExclusive and value < self._bottom:
                return False, self.tr('{} cannot be less than {}.'.format(self._name, self._bottom))

        if self._top is not None:
            if self._topExclusive and value >= self._top:
                return False, self.tr('{} must be less than {}.'.format(self._name, self._top))

            if not self._topExclusive and value > self._top:
                return False, self.tr('{} cannot be greator than {}.'.format(self._name, self._top))

        return True, None
