#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.main_window.empty_page import EmptyPage


class ContentView:
    _EMPTY_PAGE_INDEX = 0

    def __init__(self, stackedWidget, mainWindow):
        self._ui = stackedWidget
        self._emptyPage = EmptyPage(mainWindow)

    def changePane(self, index):
        self._ui.setCurrentIndex(index)

    def page(self, index):
        return self._ui.widget(index)

    def addPage(self, page):
        return self._ui.addWidget(page)
