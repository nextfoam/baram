#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.pane.empty_page import EmptyPage
from view.pane.empty_pane import EmptyPane
from view.pane.list_page import ListPage
from view.pane.list_pane import ListPane


class FormView:
    _EMPTY_PAGE_INDEX = 0
    _LIST_PAGE_INDEX = 1

    def __init__(self, stackedWidget, mainWindow):
        self._ui = stackedWidget
        self._emptyPage = EmptyPage(mainWindow)
        self._listPage = ListPage(mainWindow)

    def changePane(self, index):
        self._ui.setCurrentIndex(index)

    def page(self, index):
        return self._ui.widget(index)

    def addPage(self, pane):
        if isinstance(pane, EmptyPane):
            pane.ui = self._emptyPage
            return self._EMPTY_PAGE_INDEX
        elif isinstance(pane, ListPane):
            pane.ui = self._listPage
            return self._LIST_PAGE_INDEX
        else:
            return self._ui.addWidget(pane.create_page())

    def initPage(self, index):
        self.page(index).init()
