#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel


class AspectRatioLabel(QLabel):
    MAX_MOUSE_MOVE = 5  # In the unit of manhattanLength

    clicked = Signal(QMouseEvent)

    def setPixmap(self, pm: QPixmap) -> None:
        self._updatePixmap(pm)

    def resizeEvent(self, ev: QResizeEvent) -> None:
        self._updatePixmap()
        super(AspectRatioLabel, self).resizeEvent(ev)

    def _updatePixmap(self, pm: QPixmap = None):
        if pm is not None:
            self._pm = pm

        if self._pm is None:
            return

        spm = self._pm.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        hm = (self.width() - spm.width()) // 2
        vm = (self.height() - spm.height()) // 2

        self.setContentsMargins(hm, vm, hm, vm)

        super(AspectRatioLabel, self).setPixmap(spm)

    def mousePressEvent(self, ev: QMouseEvent):
        self._pressPos: QPoint = ev.globalPos()

        return super().mousePressEvent(ev)
    
    def mouseReleaseEvent(self, ev: QMouseEvent):
        p =  ev.globalPos() - self._pressPos
        if p.manhattanLength() < self.MAX_MOUSE_MOVE:
            self.clicked.emit(ev)

        return super().mouseReleaseEvent(ev)