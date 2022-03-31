#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .list_pane import ListPane


class ModelsPane(ListPane):
    STACKED_INDEX = 1

    def __init__(self):
        super().__init__()
        self._index = self.STACKED_INDEX

    def load(self, ui):
        ui.add("Multiphane / Off")
        ui.add("Viscous / Off")
        ui.add("Radiation / Off")
        ui.add("Species / Off")

    def save(self):
        pass
