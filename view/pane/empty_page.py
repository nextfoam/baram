#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .pane_page import PanePage


class EmptyPage(PanePage):
    def __init__(self, widget):
        super().__init__(widget)

    def init(self):
        pass
