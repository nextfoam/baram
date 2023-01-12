#!/usr/bin/env python
# -*- coding: utf-8 -*-

from view.main_window.empty_page import EmptyPage


class ContentView:
    _EMPTY_PAGE_INDEX = 0

    def __init__(self, stackedWidget, mainWindow):
        self._view = stackedWidget
        self._emptyPage = EmptyPage(mainWindow)

    def changePane(self, index):
        self._view.setCurrentIndex(index)

    def page(self, index):
        return self._view.widget(index)

    def addPage(self, page):
        return self._view.addWidget(page)

    def removePage(self, index):
        self._view.removeWidget(self._view.widget(index))

    def currentPage(self):
        return self._view.currentWidget() if self._view.currentIndex() > 0 else None
