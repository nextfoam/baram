#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QWidget, QFrame, QSizePolicy

from widgets.aspect_ratio_label import AspectRatioLabel


class _EdgeGrabHandle(QWidget):
    """Thin strip along the frame's right edge that owns the resize cursor and drag gesture.

    Its cursor is set once and never touched again: Qt shows a widget's own cursor
    whenever the pointer is over it and restores whatever applies elsewhere the
    moment the pointer leaves, so no enter/leave/move bookkeeping is needed to
    "restore" it.
    """

    def __init__(self, frame: 'OverlayFrame'):
        super().__init__(frame)

        self._frame = frame

        self.setCursor(Qt.CursorShape.SizeHorCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._frame.beginResize(event.globalPos())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._frame.isResizing():
            self._frame.continueResize(event.globalPos())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._frame.isResizing():
            self._frame.endResize()
            event.accept()
            return

        super().mouseReleaseEvent(event)


class OverlayFrame(QFrame):
    MARGIN = 0
    EDGE_GRAB_MARGIN = 6  # width in px of the draggable strip along the right edge
    MIN_WIDTH = 250

    collapsed = Signal(bool)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setAutoFillBackground(True)

        self._resizing = False
        self._resizeStartMouseX = 0
        self._resizeStartWidth = 0

        self._content = QWidget(self)
        self._edgeHandle = _EdgeGrabHandle(self)
        self._edgeHandle.setAutoFillBackground(True)
        self._edgeHandle.setFixedWidth(self.EDGE_GRAB_MARGIN)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._content, 1)
        layout.addWidget(self._edgeHandle)

        self._rightArrow = QPixmap(u":/icons/chevron-forward.svg")
        self._leftArrow = QPixmap(u":/icons/chevron-back.svg")

        self._toggleHandle = AspectRatioLabel(parent)

        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self._toggleHandle.sizePolicy().hasHeightForWidth())

        self._toggleHandle.setAutoFillBackground(True)
        self._toggleHandle.setPixmap(self._rightArrow)
        self._toggleHandle.setSizePolicy(sizePolicy)
        self._toggleHandle.setMinimumSize(QSize(18, 72))
        self._toggleHandle.setMaximumSize(QSize(18, 72))

        self._animPanel = QPropertyAnimation(self, b"pos")
        self._animPanel.setEasingCurve(QEasingCurve.InOutCubic)

        self._animHandle = QPropertyAnimation(self._toggleHandle, b"pos")
        self._animHandle.setEasingCurve(QEasingCurve.InOutCubic)

        self._agroup = QParallelAnimationGroup()
        self._agroup.addAnimation(self._animPanel)
        self._agroup.addAnimation(self._animHandle)

        self._collapsed = True

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._toggleHandle.clicked.connect(self._handleClicked)
        self._agroup.finished.connect(self._animationFinished)

    def isCollapsed(self) -> bool:
        return self._collapsed

    def content(self) -> QWidget:
        """Parent for external UI content — never the frame itself, so it can't cover the edge handle."""
        return self._content

    def isResizing(self) -> bool:
        return self._resizing

    def beginResize(self, globalPos: QPoint):
        self._resizing = True
        self._resizeStartMouseX = globalPos.x()
        self._resizeStartWidth = self.width()

    def continueResize(self, globalPos: QPoint):
        delta = globalPos.x() - self._resizeStartMouseX
        newWidth = min(max(self._resizeStartWidth + delta, self.MIN_WIDTH), self._maxWidth())
        self.resize(newWidth, self.height())
        self.reflow()

    def endResize(self):
        self._resizing = False

    def _parentRect(self):
        if hasattr(self.parent(), 'viewport'):
            return self.parent().viewport().rect()
        else:
            return self.parent().rect()

    def _maxWidth(self) -> int:
        parentRect = self._parentRect()
        if not parentRect:
            return self.MIN_WIDTH

        return max(self.MIN_WIDTH, parentRect.width() - self._toggleHandle.width())

    def reflow(self):
        parentRect = self._parentRect()

        if not parentRect:
            return

        width = min(max(self.width(), self.MIN_WIDTH), self._maxWidth())

        if self._collapsed:
            self.setGeometry(-width, self.MARGIN, width, parentRect.height()-self.MARGIN*2)
            handleX = 0
        else:
            self.setGeometry(0, self.MARGIN, width, parentRect.height()-self.MARGIN*2)
            handleX = width

        self._toggleHandle.setGeometry(handleX, self.MARGIN + (self.height() - self._toggleHandle.height()) // 2, self._toggleHandle.width(), self._toggleHandle.height())

    def showEvent(self, event):
        if not event.spontaneous():
            self.reflow()

        return super(OverlayFrame, self).showEvent(event)

    def _handleClicked(self, ev: QMouseEvent):
        if self._agroup.state() == QAbstractAnimation.Running:
            return

        if self._collapsed:
            self._animPanel.setEndValue(QPoint(0, self.pos().y()))
            self._animHandle.setEndValue(QPoint(self.width(), self._toggleHandle.pos().y()))
            self._agroup.start()
        else:
            self._animPanel.setEndValue(QPoint(-self.width(), self.pos().y()))
            self._animHandle.setEndValue(QPoint(0, self._toggleHandle.pos().y()))
            self._agroup.start()

    def _animationFinished(self):
        if self._collapsed:
            self._collapsed = False
            self._toggleHandle.setPixmap(self._leftArrow)
            self.collapsed.emit(False)
        else:
            self._collapsed = True
            self._toggleHandle.setPixmap(self._rightArrow)
            self.collapsed.emit(True)

    def _updateView(self):
        pass
