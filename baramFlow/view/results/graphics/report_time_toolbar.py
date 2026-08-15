#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QEvent, QPoint, QTimer, Signal
from PySide6.QtGui import QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from resources import resource

from widgets.themed_icon import load_themed_icon
from widgets.time_slider import TimeSlider

from .report_time_toolbar_ui import Ui_ReportTimeToolbar


class ReportTimeToolbar(QWidget):
    timeSelected = Signal(str)
    playClicked = Signal()
    stopClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_ReportTimeToolbar()
        self._ui.setupUi(self)

        self._playIcon = load_themed_icon(':/icons/play.svg')
        self._stopIcon = load_themed_icon(':/icons/stop.svg')
        self._ui.playButton.setIcon(self._playIcon)

        # The source image is one exact repeat period of a scrolling-stripe
        # texture, drawn directly in busyLabel's paint event (rather than via
        # setPixmap()) so the pattern can be tiled with a scroll offset without
        # ever affecting busyLabel's own size hint — setPixmap()-ing a tile sized
        # to the label's *current* width once created a feedback loop where every
        # growth permanently inflated the minimum width of the whole ancestor
        # chain, since nothing ever shrank it back (this is what broke restoring
        # after maximizing). Motion is a plain offset advanced on a timer, not
        # pre-rendered animation frames, since there's only one static tile.
        self._busyTile = QPixmap(str(resource.file('images/loadingAnimation.png')))
        self._busyOffset = 0
        self._busyTimer = QTimer(self)
        self._busyTimer.setInterval(40)
        self._busyTimer.timeout.connect(self._advanceBusyOffset)
        self._ui.busyLabel.installEventFilter(self)

        # Not part of outerLayout — it floats above everything, tracking the slider
        # handle's position on every time change. Starts out parented to this
        # widget, but it needs to end up parented to a common ancestor of both this
        # toolbar and the 3D view beneath it (see setOverlayParent), or it would be
        # clipped/painted-under by whatever is outside this toolbar's own bounds.
        self._currentTimeLabel = QLabel(self)
        self._currentTimeLabel.setStyleSheet(
            'background-color: palette(tooltip-base); color: palette(tooltip-text);'
            'border: 1px solid palette(dark); padding: 0px 3px;')
        self._overlayParent = self
        self._currentTimeLabel.raise_()

        self._timeSlider = TimeSlider(self._ui.slider, self._ui.lastTime)

        self._playing = False
        self._currentTimeLabel.hide()

        self._ui.playButton.clicked.connect(self._playButtonClicked)
        self._timeSlider.currentTimeChanged.connect(self.timeSelected)
        self._timeSlider.currentTimeChanged.connect(self._updateCurrentTimeLabel)

        # currentTimeChanged only fires on release (the slider tracks lazily so a
        # drag doesn't trigger a reload per pixel) — sliderMoved fires continuously
        # during the drag itself, which is what the label needs to actually follow
        # the handle rather than jump once at the end.
        self._ui.slider.sliderMoved.connect(self._sliderMoved)

        self._updateCurrentTimeLabel(self._timeSlider.getCurrentTime())

    def eventFilter(self, watched, event):
        if watched is self._ui.busyLabel:
            if event.type() == QEvent.Type.Paint:
                self._drawBusyFrame()
                return True

            if event.type() == QEvent.Type.Resize:
                # Watching busyLabel's own resize rather than this widget's: when
                # this widget resizes, Qt's layout pass that actually grows
                # busyLabel to match can still be pending, so reading positions
                # from here right away can catch stale geometry.
                self._repositionCurrentTimeLabel()

        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # A window maximize/restore resizes everything through a different, less
        # predictable event cascade than an interactive drag-resize — busyLabel's
        # own resize event isn't reliably delivered as part of it (nor is its
        # timing relative to this one), so this widget's own resize is watched too,
        # deferred so it reads geometry only after Qt's relayout has fully settled.
        QTimer.singleShot(0, self._repositionCurrentTimeLabel)

    def setOverlayParent(self, parent: QWidget):
        """Reparents the current-time label onto a common ancestor of this toolbar
        and whatever sits below it (e.g. the 3D view), so it can float above both
        instead of being clipped to this toolbar's own small bounds."""
        self._overlayParent = parent
        self._currentTimeLabel.setParent(parent)
        self._currentTimeLabel.raise_()

    def _playButtonClicked(self):
        if self._playing:
            # The actual stop isn't instant — the play loop only notices the
            # request after the in-flight step finishes. Disabling immediately
            # acknowledges the click instead of leaving it looking clickable
            # while nothing happens (and blocks a rapid double-click).
            self._ui.playButton.setEnabled(False)
            self.stopClicked.emit()
        else:
            self.playClicked.emit()

    def setPlaying(self, playing: bool):
        self._playing = playing
        self._ui.playButton.setEnabled(True)
        self._ui.playButton.setIcon(self._stopIcon if playing else self._playIcon)
        self._ui.playButton.setToolTip(self.tr('Stop') if playing else self.tr('Play'))

        # Only shown during Play — the real hover tooltip already covers manual
        # scrubbing, and the two would otherwise sit on top of each other.
        if playing:
            self._repositionCurrentTimeLabel()
        else:
            self._currentTimeLabel.hide()

    def setSliderEnabled(self, enabled: bool):
        if enabled:
            self._timeSlider.setEnable()
        else:
            self._timeSlider.setDisable()

    def setPlayButtonEnabled(self, enabled: bool):
        self._ui.playButton.setEnabled(enabled)

    def setBusy(self, busy: bool):
        if busy:
            self._busyTimer.start()
        else:
            self._busyTimer.stop()
            self._busyOffset = 0
            self._ui.busyLabel.update()

    def _advanceBusyOffset(self):
        # drawTiledPixmap's offset is the point in the (infinitely tiled) source
        # that lands at the destination's top-left corner — increasing it slides
        # the visible window rightward through the source, which makes the pattern
        # appear to move left. Decrementing (Python's % wraps negatives correctly)
        # makes it flow right instead.
        self._busyOffset = (self._busyOffset - 1) % self._busyTile.width()
        self._ui.busyLabel.update()

    def _drawBusyFrame(self):
        if self._busyTile.isNull():
            return

        rect = self._ui.busyLabel.rect()
        painter = QPainter(self._ui.busyLabel)
        painter.drawTiledPixmap(rect, self._busyTile, QPoint(self._busyOffset, 0))

        pen = painter.pen()
        pen.setColor(self._ui.busyLabel.palette().color(QPalette.ColorRole.Dark))
        painter.setPen(pen)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

    def _sliderMoved(self, index: int):
        self._updateCurrentTimeLabel(self._timeSlider.getTimeValues()[index])

    def _updateCurrentTimeLabel(self, time: str):
        self._currentTimeLabel.setText(time)
        self._currentTimeLabel.adjustSize()
        self._repositionCurrentTimeLabel()

    def _repositionCurrentTimeLabel(self):
        if not self._playing:
            return

        # slider, busyLabel and the overlay parent may be arbitrarily far apart in
        # the widget tree (the overlay parent is deliberately an ancestor several
        # levels up) — global coordinates are the only mapping that's always valid
        # regardless of exactly how they're nested.
        handleGlobalX = self._ui.slider.mapToGlobal(self._timeSlider.handleRect().center()).x()
        barGlobalTop = self._ui.busyLabel.mapToGlobal(QPoint(0, 0)).y()
        origin = self._overlayParent.mapFromGlobal(QPoint(handleGlobalX, barGlobalTop))

        label = self._currentTimeLabel
        x = origin.x() - label.width() // 2
        x = max(0, min(x, self._overlayParent.width() - label.width()))

        label.move(x, origin.y())
        label.raise_()
        label.show()

    def updateTimeValues(self, timeValues: list[str]):
        self._timeSlider.updateTimeValues(timeValues)

    def setCurrentTime(self, time: str):
        self._timeSlider.setCurrentTime(time)

    def getCurrentTime(self) -> str:
        return self._timeSlider.getCurrentTime()

    def getTimeValues(self) -> list[str]:
        return self._timeSlider.getTimeValues()

    def hasMoreTimes(self) -> bool:
        timeValues = self.getTimeValues()
        return bool(timeValues) and self.getCurrentTime() != timeValues[-1]
