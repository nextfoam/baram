#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from baramFlow.view.widgets.resizable_dialog import ResizableDialog

from .option_dialog_ui import Ui_OptionDialog


class OptionType(Enum):
    BOX = 0
    CYLINDER = auto()
    CELL_ZONE = auto()


class OptionDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_OptionDialog()
        self._ui.setupUi(self)

        self._connectSignalsSlots()

        self._ui.type.setCurrentIndex(0)

    def _connectSignalsSlots(self):
        self._ui.type.currentIndexChanged.connect(self._typeChanged)

    def _typeChanged(self):
        self._ui.box.setVisible(self._ui.type.currentIndex() == OptionType.BOX.value)
        self._ui.cylinder.setVisible(self._ui.type.currentIndex() == OptionType.CYLINDER.value)
        self._ui.cellZone.setVisible(self._ui.type.currentIndex() == OptionType.CELL_ZONE.value)
