#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pane import Pane


class ListPane(Pane):
    def __init__(self):
        super().__init__()

    def create_page(self):
        pass

    # virtual
    def load(self, ui):
        pass

    # virtual
    def save(self):
        pass
