#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox


class PythonComboBox(QComboBox):
    """QComboBox that uses Python for equivalance check

    As PySide6 does not support QVariant,
    the equivalence of Python object of custom class is checked by object id.
    This class uses "__eq__" of Python to find a Data(Python Object).
    """

    def findData(self, data, role=Qt.ItemDataRole.UserRole):
        for i in range(self.count()):
            if data == self.itemData(i, role):
                return i

        return -1

