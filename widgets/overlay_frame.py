#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, QSize, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QWidget, QFrame, QSizePolicy

from widgets.aspect_ratio_label import AspectRatioLabel


class OverlayFrame(QFrame):
    MARGIN = 0
    collapsed = Signal(bool)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setAutoFillBackground(True)

        self._rightArrow = QPixmap(u":/icons/chevron-forward.svg")
        self._leftArrow = QPixmap(u":/icons/chevron-back.svg")

        self._controlHandle = AspectRatioLabel(parent)

        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self._controlHandle.sizePolicy().hasHeightForWidth())

        self._controlHandle.setAutoFillBackground(True)
        self._controlHandle.setPixmap(self._rightArrow)
        self._controlHandle.setSizePolicy(sizePolicy)
        self._controlHandle.setMinimumSize(QSize(18, 72))
        self._controlHandle.setMaximumSize(QSize(18, 72))

        self._animPanel = QPropertyAnimation(self, b"pos")
        self._animPanel.setEasingCurve(QEasingCurve.InOutCubic)

        self._animHandle = QPropertyAnimation(self._controlHandle, b"pos")
        self._animHandle.setEasingCurve(QEasingCurve.InOutCubic)

        self._agroup = QParallelAnimationGroup()
        self._agroup.addAnimation(self._animPanel)
        self._agroup.addAnimation(self._animHandle)

        self._collapsed = True

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._controlHandle.clicked.connect(self._handleClicked)
        self._agroup.finished.connect(self._animationFinished)

    def isCollapsed(self) -> bool:
        return self._collapsed

    def updateGeometry(self):
        if hasattr(self.parent(), 'viewport'):
            parentRect = self.parent().viewport().rect()
        else:
            parentRect = self.parent().rect()

        if not parentRect:
            return

        if self._collapsed:
            self.setGeometry(-self.width(), self.MARGIN, self.width(), parentRect.height()-self.MARGIN*2)
            handleX = 0
        else:
            self.setGeometry(0, self.MARGIN, self.width(), parentRect.height()-self.MARGIN*2)
            handleX = self.width()

        self._controlHandle.setGeometry(handleX, self.MARGIN + (self.height() - self._controlHandle.height()) // 2, self._controlHandle.width(), self._controlHandle.height())

    def showEvent(self, event):
        if not event.spontaneous():
            self.updateGeometry()

        return super(OverlayFrame, self).showEvent(event)

    def _handleClicked(self, ev: QMouseEvent):
        if self._agroup.state() == QAbstractAnimation.Running:
            return

        if self._collapsed:
            self._animPanel.setEndValue(QPoint(0, self.pos().y()))
            self._animHandle.setEndValue(QPoint(self.width(), self._controlHandle.pos().y()))
            self._agroup.start()
        else:
            self._animPanel.setEndValue(QPoint(-self.width(), self.pos().y()))
            self._animHandle.setEndValue(QPoint(0, self._controlHandle.pos().y()))
            self._agroup.start()

    def _animationFinished(self):
        if self._collapsed:
            self._collapsed = False
            self._controlHandle.setPixmap(self._leftArrow)
            self.collapsed.emit(False)
        else:
            self._collapsed = True
            self._controlHandle.setPixmap(self._rightArrow)
            self.collapsed.emit(True)

    def _updateView(self):
        pass