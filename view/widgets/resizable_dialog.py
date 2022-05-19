#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QFormLayout

class ResizableForm:
    class Row:
        def __init__(self):
            self._label = None
            self._field = None
            self._flag = False
            self._visible = True

        @property
        def label(self):
            return self._label

        @property
        def field(self):
            return self._field

        @property
        def flag(self):
            return self._flag

        @flag.setter
        def flag(self, flag):
            self._flag = flag

        def setToHide(self, label, field):
            """Set properties for the row to hide - Backup widgets and clear flag

            Args:
                label: Label widget to backup
                field: Field widget or layout to backup
            """
            self._label = label
            self._field = field
            self._label.setParent(None)
            self._field.setParent(None)
            self._flag = False
            self._visible = False

        def setToShow(self):
            """Set properties for the row to show - Clear backup and flag
            """
            self._label = None
            self._field = None
            self._flag = False
            self._visible = True

        def isVisible(self):
            return self._visible

    def __init__(self, layout):
        self._layout = layout
        self._rows = [self.Row() for _ in range(layout.rowCount())]

    def setRowsVisible(self, rows, visible):
        """Set Visibility of the rows

        Args:
            rows: List of row indices
            visible: Whether the row is visible

        Returns:

        """
        if visible:
            for r in rows:
                if not self._rows[r].isVisible():
                    self._rows[r].flag = True

            index = 0
            for i in range(len(self._rows)):
                if self._rows[i].isVisible():
                    index = index + 1
                elif self._rows[i].flag:
                    self._layout.insertRow(index, self._rows[i].label, self._rows[i].field)
                    self._rows[i].setToShow()
                    index = index + 1
        else:
            for r in rows:
                if self._rows[r].isVisible():
                    self._rows[r].flag = True

            index = 0
            for i in range(len(self._rows)):
                if self._rows[i].isVisible():
                    if self._rows[i].flag:
                        label = self._layout.itemAt(index, QFormLayout.LabelRole)
                        field = self._layout.itemAt(index, QFormLayout.FieldRole)

                        self._rows[i].setToHide(label.widget(), field.layout() or field.widget())

                        self._layout.removeItem(label)
                        self._layout.removeItem(field)
                        self._layout.removeRow(index)
                    else:
                        index = index + 1

class ResizableDialog(QDialog):
    def __init__(self):
        super().__init__()

    def _setGroupVisible(self, widgetList, visible):
        for widget in widgetList:
            widget.setVisible(visible)

    def _resizeDialog(self, widget):
        oldWidth = self.width()
        oldHeight = self.height()

        while widget is not None:
            widget.adjustSize()
            widget = widget.parent()

        width = self.width()
        height = self.height()

        # Force the dialog to resize to adjust children's size
        if width == oldWidth and height == oldHeight:
            self.resize(width + 1, height + 1)
            self.resize(width, height)
