#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QGroupBox, QFormLayout, QLineEdit, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal

class BoundaryWidget(QWidget):
    selectButtonClicked = Signal()
    
    def __init__(self):
        super().__init__()
        
        self._boundary = QLineEdit(self)
        self._boundary.setEnabled(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._boundary)

        button = QPushButton(self.tr('Select'), self)
        button.clicked.connect(self.selectButtonClicked)
        layout.addWidget(button)
        
    def setText(self, boundary):
        self._boundary.setText(boundary)
        
    def text(self):
        return self._boundary.text()
    

class Export2DPlaneRegionWidget(QGroupBox):
    boundarySelectClicked = Signal(BoundaryWidget)

    def __init__(self, rname):
        super().__init__()

        self._rname = rname
        self._boundary = BoundaryWidget()

        self.setTitle(rname)
                
        layout = QFormLayout(self)
        layout.addRow(QLabel(self.tr('Boundary')), self._boundary)
        
        self._connectSignalsSlots()
        
    def rname(self):
        return self._rname
    
    def boundary(self):
        return self._boundary.text()
        
    def _connectSignalsSlots(self):
        self._boundary.selectButtonClicked.connect(lambda: self.boundarySelectClicked.emit(self._boundary))
    

class Export2DWedgeRegionWidget(QGroupBox):
    p1SelectClicked = Signal(BoundaryWidget)
    p2SelectClicked = Signal(BoundaryWidget)

    def __init__(self, rname):
        super().__init__()

        self._rname = rname
        self._p1 = BoundaryWidget()
        self._p2 = BoundaryWidget()
    
        self.setTitle(rname)
                
        layout = QFormLayout(self)
        layout.addRow(QLabel(self.tr('Source Boundary, P1')), self._p1)
        layout.addRow(QLabel(self.tr('Exposed Boundary, P2')), self._p2)
        
        self._connectSignalsSlots()
        
    def rname(self):
        return self._rname
    
    def p1(self):
        return self._p1.text()
    
    def p2(self):
        return self._p2.text()
        
    def _connectSignalsSlots(self):
        self._p1.selectButtonClicked.connect(lambda: self.p1SelectClicked.emit(self._p1))
        self._p2.selectButtonClicked.connect(lambda: self.p2SelectClicked.emit(self._p2))
        