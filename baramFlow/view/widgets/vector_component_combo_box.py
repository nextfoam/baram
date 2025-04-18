#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.field import VECTOR_COMPONENT_TEXTS, VectorComponent
from widgets.python_combo_box import PythonComboBox


class VectorComponentComboBox(PythonComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for component in VectorComponent:
            self.addItem(VECTOR_COMPONENT_TEXTS[component], component)

        self.setCurrentIndex(0)

