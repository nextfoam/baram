#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pane import Pane


class EmptyPane(Pane):
    def __init__(self):
        super().__init__()

    def create_page(self):
        pass

    def load(self):
        pass

    def save(self):
        pass
