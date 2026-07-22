#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QWidget


class ContentPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

    @qasync.asyncSlot()
    async def saveSlot(self):
        return await self.save()

    async def save(self):
        return True

    async def checkToQuit(self):
        return True
