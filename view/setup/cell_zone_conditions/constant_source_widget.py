#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from .constant_source_widget_ui import Ui_ConstantSourceWidget


class ConstantSourceWidget(QWidget):
    def __init__(self, texts):
        """Constructs a new widget for setting the constant source term.

        Args:
            texts: List of texts for the labels : [title of the groupBox, label of the value]
        """
        super().__init__()
        self._ui = Ui_ConstantSourceWidget()
        self._ui.setupUi(self)

        self._ui.groupBox.setTitle(texts["title"])
        self._ui.label.setText(texts["label"])
