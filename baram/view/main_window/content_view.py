#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baram.view.main_window.empty_page import EmptyPage


class ContentView:
    def __init__(self, stackedWidget, mainWindow):
        self._view = stackedWidget
        self._emptyPage = EmptyPage(mainWindow)

    def changePane(self, page):
        self._view.setCurrentWidget(page.widget)

    def addPage(self, page):
        return self._view.addWidget(page.widget)

    def removePage(self, page):
        self._view.removeWidget(page.widget)

    def currentPage(self):
        return self._view.currentWidget() if self._view.currentIndex() > 0 else None
