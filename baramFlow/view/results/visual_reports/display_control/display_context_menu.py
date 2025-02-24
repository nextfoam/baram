from baramFlow.view.results.visual_reports.display_control.opacity_dialog import OpacityDialog
from baramMesh.rendering.actor_info import DisplayMode, Properties


from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import QColorDialog, QMenu


class DisplayContextMenu(QMenu):
    showActionTriggered = Signal()
    hideActionTriggered = Signal()
    opacitySelected = Signal(float)
    colorPicked = Signal(QColor)
    noCutActionTriggered = Signal(bool)

    wireframeDisplayModeSelected = Signal()
    surfaceDisplayModeSelected = Signal()
    surfaceEdgeDisplayModeSelected = Signal()

    def __init__(self, parent):
        super().__init__(parent)

        self._opacityDialog = OpacityDialog(parent)
        self._colorDialog = QColorDialog(parent)
        self._colorDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._properties = None

        self._showAction = self.addAction(self.tr('Show'), lambda: self.showActionTriggered.emit())
        self._hideAction = self.addAction(self.tr('Hide'), lambda: self.hideActionTriggered.emit())
        self._opacityAction = self.addAction(self.tr('Opacity'), self._openOpacityDialog)
        self._colorAction = self.addAction(self.tr('Color'), self._openColorDialog)

        displayMenu = self.addMenu(self.tr('Display Mode'))
        self._wireFrameDisplayAction = displayMenu.addAction(
            self.tr('Wireframe'), lambda: self.wireframeDisplayModeSelected.emit())
        self._surfaceDisplayAction = displayMenu.addAction(
            self.tr('Surface'), lambda: self.surfaceDisplayModeSelected.emit())
        self._surfaceEdgeDisplayAction = displayMenu.addAction(
            self.tr('Surface with Edges'), lambda: self.surfaceEdgeDisplayModeSelected.emit())

        self._noCutAction: QAction = self.addAction(self.tr('No Cut'), self._noCutActionTriggered)

        self._wireFrameDisplayAction.setCheckable(True)
        self._surfaceDisplayAction.setCheckable(True)
        self._surfaceEdgeDisplayAction.setCheckable(True)
        self._noCutAction.setCheckable(True)

        self._connectSignalsSlots()

    def execute(self, pos, properties: Properties):
        self._properties = properties

        self._showAction.setVisible(not properties.visibility)
        self._hideAction.setVisible(properties.visibility is None or properties.visibility)
        self._wireFrameDisplayAction.setChecked(properties.displayMode == DisplayMode.WIREFRAME)
        self._surfaceDisplayAction.setChecked(properties.displayMode == DisplayMode.SURFACE)
        self._surfaceEdgeDisplayAction.setChecked(properties.displayMode == DisplayMode.SURFACE_EDGE)
        self._noCutAction.setChecked(properties.cutEnabled is False)

        self.exec(pos)

    def _connectSignalsSlots(self):
        self._opacityDialog.accepted.connect(lambda: self.opacitySelected.emit(self._opacityDialog.opacity()))
        self._colorDialog.accepted.connect(lambda: self.colorPicked.emit(self._colorDialog.selectedColor()))

    def _openOpacityDialog(self):
        self._opacityDialog.setOpacity(self._properties.opacity)
        self._opacityDialog.show()

    def _openColorDialog(self):
        self._colorDialog.setCurrentColor(
            Qt.GlobalColor.white if self._properties.color is None else self._properties.color)
        self._colorDialog.show()

    def _noCutActionTriggered(self):
        self.noCutActionTriggered.emit(not self._properties.cutEnabled)