from typing import Callable

from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkInteractionWidgets import vtkBorderRepresentation, vtkScalarBarWidget


class ScalarBarWidget(vtkScalarBarWidget):

    def __init__(self, callback: Callable[[], None]):
        super().__init__()

        self._callback = callback

        self._doubleClickTag = None
        self._dialog = None

        self._enableTag  = self.AddObserver(vtkCommand.EnableEvent, self._enabled)
        self._disableTag = self.AddObserver(vtkCommand.DisableEvent, self._disabled)

    def _enabled(self, obj, event):
        interactor = self.GetInteractor()
        self._doubleClickTag = interactor.AddObserver(vtkCommand.LeftButtonDoubleClickEvent, self._leftButtonDoubleClickEvent)

    def _disabled(self, obj, event):
        self._removeDoubleClickObserver()

    def __del__(self):
        self._removeDoubleClickObserver()

    def _removeDoubleClickObserver(self):
        if self._doubleClickTag is None:
            return

        interactor = self.GetInteractor()
        interactor.RemoveObserver(self._doubleClickTag)
        self._doubleClickTag = None

    def _leftButtonDoubleClickEvent(self, obj, event):
        representation = self.GetScalarBarRepresentation()
        if representation.GetInteractionState() == vtkBorderRepresentation.Outside:
            return

        self._callback()