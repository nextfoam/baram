#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QWidget, QFrame, QSizePolicy

from widgets.aspect_ratio_label import AspectRatioLabel


class OverlayFrame(QFrame):
    MARGIN = 0
    EDGE_GRAB_MARGIN = 6  # width in px of the draggable strip along the right edge
    MIN_WIDTH = 250

    collapsed = Signal(bool)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setAutoFillBackground(True)
        self.setMouseTracking(True)

        self._resizing = False
        self._resizeStartMouseX = 0
        self._resizeStartWidth = 0

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

    def _parentRect(self):
        if hasattr(self.parent(), 'viewport'):
            return self.parent().viewport().rect()
        else:
            return self.parent().rect()

    def _maxWidth(self) -> int:
        parentRect = self._parentRect()
        if not parentRect:
            return self.MIN_WIDTH

        return max(self.MIN_WIDTH, parentRect.width() - self._controlHandle.width())

    def _isOnRightEdge(self, pos: QPoint) -> bool:
        return (not self._collapsed) and ((self.width() - self.EDGE_GRAB_MARGIN) <= pos.x() <= self.width())

    def updateGeometry(self):
        parentRect = self._parentRect()

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

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._isOnRightEdge(event.pos()):
            self._resizing = True
            self._resizeStartMouseX = event.globalPos().x()
            self._resizeStartWidth = self.width()
            event.accept()
            return

        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._resizing:
            delta = event.globalPos().x() - self._resizeStartMouseX
            newWidth = min(max(self._resizeStartWidth + delta, self.MIN_WIDTH), self._maxWidth())
            self.resize(newWidth, self.height())
            self.updateGeometry()
            event.accept()
            return

        if self._isOnRightEdge(event.pos()):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.unsetCursor()

        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._resizing:
            self._resizing = False
            event.accept()
            return

        return super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if not self._resizing:
            self.unsetCursor()

        return super().leaveEvent(event)

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