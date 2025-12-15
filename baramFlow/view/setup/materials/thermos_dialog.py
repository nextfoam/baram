#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QDialog, QHeaderView, QTableWidgetItem
import qasync

from baramFlow.base.material.database import materialsBase
from baramFlow.base.material.material import DensitySpecification, MaterialType, Phase, SpecificHeatSpecification, TransportSpecification
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.view.setup.materials.thermos_dialog_ui import Ui_ThermosDialog


class ThermosDialog(QDialog):
    def __init__(self, mtype: MaterialType, phase:Phase, highlights: tuple[DensitySpecification, SpecificHeatSpecification, TransportSpecification], parent):
        super().__init__(parent)

        self._ui = Ui_ThermosDialog()
        self._ui.setupUi(self)

        self._selected_row = -1

        headers = ["Density", "Specific Heat", "Transport"]

        if phase == Phase.SOLID:
            thermoType = 'heSolidThermo'
        else:
            thermoType = 'heRhoThermo'

        self._thermos = []
        thermos = materialsBase.getThermos()
        for thermo in thermos:
            if thermo[0] != thermoType:
                continue

            if thermo[1] != mtype:
                continue

            if thermo[2] not in MaterialDB.availableDensitySpec(mtype, phase):
                continue

            if thermo[3] not in MaterialDB.availableSpecificHeatSpecs(mtype, phase):
                continue

            if thermo[4] not in MaterialDB.availableTransportSpecs(mtype, phase):
                continue

            self._thermos.append((thermo[2], thermo[3], thermo[4]))


        self._ui.thermosTable.setColumnCount(len(headers))
        self._ui.thermosTable.setRowCount(len(self._thermos))

        self._ui.thermosTable.setHorizontalHeaderLabels(headers)
        self._ui.thermosTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Set Excel-like header styling
        self.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                padding: 4px;
                font-weight: bold;
            }
            QHeaderView::section:horizontal {
                border-bottom: 2px solid #d0d0d0;
            }
            QHeaderView::section:vertical {
                border-right: 2px solid #d0d0d0;
            }
        """)

        for rowIndex, thermo in enumerate(self._thermos):
            item = QTableWidgetItem(MaterialDB.densitySpecToText(thermo[0]))
            if thermo[0] == highlights[0]:
                item.setBackground(QBrush(QColor(255, 255, 200)))  # Light yellow
            self._ui.thermosTable.setItem(rowIndex, 0, item)

            item = QTableWidgetItem(MaterialDB.specificHeatSpecToText(thermo[1]))
            if thermo[1] == highlights[1]:
                item.setBackground(QBrush(QColor(255, 255, 200)))  # Light yellow
            self._ui.thermosTable.setItem(rowIndex, 1, item)

            item = QTableWidgetItem(MaterialDB.transportSpecToText(thermo[2]))
            if thermo[2] == highlights[2]:
                item.setBackground(QBrush(QColor(255, 255, 200)))  # Light yellow
            self._ui.thermosTable.setItem(rowIndex, 2, item)

        loop = asyncio.get_running_loop()
        self._future = loop.create_future()

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.thermosTable.itemClicked.connect(self._onRowClicked)
        self._ui.Ok.clicked.connect(self._okClicked)
        self._ui.Cancel.clicked.connect(self._cancelClicked)

    def show(self) -> asyncio.Future:

        super().show()

        return self._future

    def _onRowClicked(self, item):
        self._selected_row = item.row()

    @qasync.asyncSlot()
    async def _okClicked(self):
        if not self._future.done():
            thermo = self._thermos[self._selected_row]
            self._future.set_result((thermo[0], thermo[1], thermo[2]))

        self.close()

    def _cancelClicked(self):
        if not self._future.cancelled():
            self._future.cancel()

        self.close()

    def closeEvent(self, event):
        if not self._future.done():
            self._future.cancel()

        event.accept()
