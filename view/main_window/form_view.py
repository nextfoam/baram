#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.pane.empty_page import EmptyPage
from view.pane.list_page import ListPage


class FormView:
    def __init__(self, stackedWidget, mainWindow):
        self._ui = stackedWidget
        self._emptyPage = EmptyPage(mainWindow)
        self._listPage = ListPage(mainWindow)

    def changePane(self, index):
        self._ui.setCurrentIndex(index)

    def page(self, index):
        if index == 0:
            return self._emptyPage
        elif index == 1:
            return self._listPage
        return self._ui.widget(index)

    def addPage(self, page):
        return self._ui.addWidget(page)

    def initPage(self, index):
        self.page(index).init()
