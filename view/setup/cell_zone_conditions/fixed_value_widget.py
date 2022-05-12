#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .fixed_value_widget_ui import Ui_FixedValueWidget


class FixedValueWidget(QWidget):
    def __init__(self, texts):
        """Constructs a new widget for setting the fixed value of the cell zone conditions.

        Args:
            texts: List of texts for the labels : [title of the groupBox, label of the value]
        """
        super().__init__()
        self._ui = Ui_FixedValueWidget()
        self._ui.setupUi(self)

        self._setup(texts)

    def _setup(self, texts):
        self._ui.groupBox.setTitle(texts["title"])
        self._ui.label.setText(texts["label"])
