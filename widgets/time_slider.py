#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import cast

from PySide6.QtCore import QEvent, QObject, QRect, Signal
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QLabel, QSlider, QStyle, QStyleOptionSlider, QToolTip

class TimeSlider(QObject):
    currentTimeChanged = Signal(str)
    lastTimeChanged = Signal(str)

    def __init__(self, uiSlider: QSlider, uiLastTime: QLabel):
        super().__init__()

        self._timeValues = ['0']

        self._uiLastTIme = uiLastTime
        self._slider = uiSlider

        self._uiLastTIme.setText('0')

        self._slider.setRange(0, 0)
        self._slider.setTracking(False)

        self._slider.sliderMoved.connect(self._sliderMoved)
        self._slider.valueChanged.connect(self._sliderValueChanged)

        self._slider.installEventFilter(self)

    def setDisable(self):
        self._slider.setEnabled(False)

    def setEnable(self):
        self._slider.setEnabled(True)

    def getCurrentTime(self) -> str:
        return self._timeValues[self._slider.value()]

    def getTimeValues(self) -> list[str]:
        return self._timeValues

    def handleRect(self) -> QRect:
        return self._slider_handle_rect()

    def setCurrentTime(self, time: str):
        if time in self._timeValues:
            index = self._timeValues.index(time)
            self._slider.setValue(index)

    def updateTimeValues(self, timeValues: list[str]):
        if (len(self._timeValues) == len(timeValues)
            and self._timeValues[-1] == timeValues[-1]):
            return

        currentTime = self._timeValues[self._slider.value()]
        if currentTime in timeValues:
            self._slider.setValue(timeValues.index(currentTime))
        else:
            self._slider.setValue(0)
            self.currentTimeChanged.emit('0')

        self._slider.setMaximum(len(timeValues)-1)

        if self._timeValues[-1] != timeValues[-1]:
            self._uiLastTIme.setText(timeValues[-1])
            self.lastTimeChanged.emit(timeValues[-1])

        self._timeValues = timeValues

    def _sliderMoved(self, index):
        self._show_dynamic_tooltip(self._timeValues[index])

    def _sliderValueChanged(self, index):
        self.currentTimeChanged.emit(self._timeValues[index])

    def _slider_handle_rect(self):
        opt = QStyleOptionSlider()
        self._slider.initStyleOption(opt)
        return self._slider.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderHandle,
            self._slider,
        )

    def _show_dynamic_tooltip(self, text: str):
        rect = self._slider_handle_rect()
        pos = self._slider.mapToGlobal(rect.center())
        QToolTip.showText(pos, text, self._slider)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            ev = cast(QHelpEvent, event)
            if self._slider_handle_rect().contains(ev.pos()):
                currentTime = self._timeValues[self._slider.value()]
                self._show_dynamic_tooltip(currentTime)

            return True

        return super().eventFilter(watched, event)

