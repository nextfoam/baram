#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import qasync
from PySide6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox

from widgets.async_message_box import AsyncMessageBox

from .batch_cases_import_dialog_ui import Ui_BatchCasesImportDialog


class BatchCasesImportDialog(QDialog):
    def __init__(self, parent, parameters):
        super().__init__(parent)
        self._ui = Ui_BatchCasesImportDialog()
        self._ui.setupUi(self)

        self._dialog = None
        self._cases = None
        self._parameters = parameters

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._connectSignalsSlots()

    def isClearChecked(self):
        return self._ui.clearOldCases.isChecked()

    def cases(self):
        return self._cases

    @qasync.asyncSlot()
    async def accept(self):
        if self._cases is None:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select file to import'))
            return

        if (self._parameters is not None
                and not self._parameters.empty
                and not self._ui.clearOldCases.isChecked()
                and (set(self._parameters.tolist()) != set(self._cases.columns.tolist()))):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('Invalid parameters. Required: ["' + '", "'.join(self._parameters) + '"]'))
            return

        super().accept()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._openFileSelectorDialog)

    def _openFileSelectorDialog(self):
        self._dialog = QFileDialog(self, self.tr('Import Batch Parameters'), '', self.tr('Excel (*.xlsx);; CSV (*.csv)'))
        self._dialog.fileSelected.connect(self._fileSelected)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _fileSelected(self, file):
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        if file.endswith('xlsx'):
            df = pd.read_excel(file, 0, header=0, index_col=0, na_filter=False, dtype=str)
        else:
            df = pd.read_csv(file, header=0, index_col=0, na_filter=False, dtype=str)

        df.columns = df.columns.str.strip()
        duplicates = set(df.columns[i] for i, duplicated in enumerate(df.columns.duplicated()) if duplicated)
        duplicates = duplicates.union(set(column[:column.find('.')] for column in df.columns if column.find('.') > 0))
        duplicates.discard('')
        if duplicates:
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('Duplicated parameters - ' + ', '.join([f'"{d}"' for d in duplicates])))
            return

        emptyColumns = [len(column) == 0 or column[:8] == 'Unnamed:' and column[0] == '.' for column in df.columns]
        for irow in range(len(df)):
            row = df.iloc[irow]
            name = df.index[irow].strip()
            for icol in range(len(row)):
                value = df.iat[irow, icol].strip()
                if value:
                    if emptyColumns[icol]:
                        await AsyncMessageBox().information(
                            self, self.tr('Input Error'), self.tr('Parameter name is empty'))
                        return
                    if not name:
                        await AsyncMessageBox().information(
                            self, self.tr('Input Error'), self.tr('Case name is empty'))
                        return

                try:
                    float(value)
                except ValueError:
                    if not value and (emptyColumns[icol] or not name):
                        df.iat[irow, icol] = ''
                    else:
                        await AsyncMessageBox().information(
                            self, self.tr('Import Error'),
                            self.tr('Value must be a float - ' + f'{name}:{df.columns[icol]}'))
                        return

        df.replace('', np.nan, inplace=True)
        df.dropna(how='all', axis=0, inplace=True)
        df.dropna(how='all', axis=1, inplace=True)

        duplicates = set(df.index[i] for i, duplicated in enumerate(df.index.duplicated()) if duplicated)
        if duplicates:
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('Duplicated case names - ' + ', '.join([f'"{d}"' for d in duplicates])))
            return

        for column in df.columns:
            if column[:8] == 'Unnamed:' or not column:
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('Parameter name is empty'))
                return

        df.index = df.index.str.strip()
        if '' in df.index:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Case name is empty'))
            return

        self._cases = df
        self._ui.file.setText(file)
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
