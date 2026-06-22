from PySide6.QtCore import QSize
from PySide6.QtWidgets import QListWidget

DEFAULT_MINIMUM_HEIGHT = 96


class ContentSizedListWidget(QListWidget):
    """QListWidget that sizes itself to fit its content."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._minimumContentHeight = DEFAULT_MINIMUM_HEIGHT

    def minimumContentHeight(self):
        return self._minimumContentHeight

    def setMinimumContentHeight(self, height):
        self._minimumContentHeight = height
        self.updateGeometry()

    def _preferredHeight(self):
        height = sum(self.sizeHintForRow(i) for i in range(self.count()))
        return max(height + 2 * self.frameWidth(), self._minimumContentHeight)

    def sizeHint(self):
        return QSize(super().sizeHint().width(), self._preferredHeight())

    def minimumSizeHint(self):
        return QSize(super().minimumSizeHint().width(), self._preferredHeight())
