#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QCheckBox


indicatorStyle = 'QCheckBox {spacing: 5px;}' \
                 'QCheckBox::indicator {width: 14px; height: 14px;}' \
                 'QCheckBox::indicator:unchecked {image: url(:/icons/chevron-forward.svg);}' \
                 'QCheckBox::indicator:checked {image: url(:icons/chevron-down.svg);}'


class FolderHeader(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._contents = None

        self._pos = None
        self._size = None

        self.setStyleSheet(indicatorStyle)

    def setContents(self, widget):
        self._contents = widget
        self._contents.setVisible(self.isChecked())
        self.toggled.connect(self._toggled)

    #
    # def showEvent(self, ev):
    #     if self._size is None:
    #         self._pos = self._contents.pos()
    #         self._size = self._contents.size()
    #         self._contents.setVisible(self.isChecked())
    #
    #         self.toggled.connect(self._toggled)

    def _toggled(self, checked):
        if checked:
            # animation = QPropertyAnimation(self._contents, b'height')
            # animation.setDuration(1000)
            # animation.setEasingCurve(QEasingCurve.Type.Linear)
            # animation.setStartValue(self._contents.geometry())
            # animation.setEndValue(QRect(self._pos.x(), self._pos.y(), self._size.width(), self._size.height()))
            # print(animation.startValue())
            # print(animation.endValue())
            # animation.start(QPropertyAnimation.DeleteWhenStopped)
            self._contents.show()
        else:
            # animation = QPropertyAnimation(self._contents, b'geometry')
            # animation.setDuration(10000)
            # animation.setEasingCurve(QEasingCurve.Type.Linear)
            # animation.setStartValue(self._contents.geometry())
            # animation.setEndValue(QRect(self._contents.x(), self._contents.y(), self._contents.width(), 0))
            # animation.start(QPropertyAnimation.DeleteWhenStopped)
            # print(animation.startValue())
            # print(animation.endValue())
            self._contents.hide()
