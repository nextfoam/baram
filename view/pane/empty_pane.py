#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pane import Pane


class EmptyPane(Pane):
    STACKED_INDEX = 0

    def __init__(self):
        super().__init__()
        self._index = self.STACKED_INDEX

    def create_page(self):
        pass

    def load(self, ui):
        pass

    def save(self):
        pass
