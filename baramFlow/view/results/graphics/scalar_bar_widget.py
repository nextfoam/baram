from typing import Callable

from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkInteractionWidgets import vtkBorderRepresentation, vtkScalarBarWidget

from baramFlow.base.graphic.graphic import Graphic


class ScalarBarWidget(vtkScalarBarWidget):

    def __init__(self, parent, report: Graphic, callback: Callable[[], None]):
        super().__init__()

        self._parent = parent
        self._report = report
        self._callback = callback

        self._doubleClickTag = None
        self._dialog = None

        self._enableTag  = self.AddObserver(vtkCommand.EnableEvent, self._enabled)
        self._disableTag = self.AddObserver(vtkCommand.DisableEvent, self._disabled)

    def _enabled(self, obj, event):
        interactor = self.GetInteractor()
        self._doubleClickTag = interactor.AddObserver(vtkCommand.LeftButtonDoubleClickEvent, self._leftButtonDoubleClickEvent)

    def _disabled(self, obj, event):
        interactor = self.GetInteractor()
        interactor.RemoveObserver(self._doubleClickTag)
        self._doubleClickTag = None

    def __del__(self):
        if self._doubleClickTag is not None:
            self._disabled()

    def _leftButtonDoubleClickEvent(self, obj, event):
        representation = self.GetScalarBarRepresentation()
        if representation.GetInteractionState() == vtkBorderRepresentation.Outside:
            return

        self._callback()