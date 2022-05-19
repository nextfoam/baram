#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QButtonGroup, QRadioButton, QVBoxLayout


class BoundaryRadioGroup(QButtonGroup):
    class BoundaryRadio(QRadioButton):
        def __init__(self, boundary):
            super().__init__(boundary["name"])
            self._boundary = boundary

    def __init__(self):
        super().__init__()

    def setup(self, widget, type_):
        boundaries = [
            {
                "id": 1,
                "name": "boundary1"
            },
            {
                "id": 2,
                "name": "boundary2"
            },
        ]

        layout = QVBoxLayout(widget)
        for boundary in boundaries:
            if type_ == type_:
                radio = self.BoundaryRadio(boundary)
                layout.addWidget(radio)
                self.addButton(radio)
        layout.addStretch()
