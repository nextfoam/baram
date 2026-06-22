#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout
)


class ConsentDialog(QDialog):
    """Modal dialog asking the user to opt in to anonymous analytics & error reporting.

    Two modes:
      - First-launch (cancellable=False, default): GDPR-friendly active opt-in;
        the dialog cannot be dismissed without a definitive Allow / Don't Allow
        choice (close button hidden, Esc key disabled).
      - Settings (cancellable=True): user can dismiss to keep the existing
        decision unchanged; Allow / Don't Allow still update consent.

    Use `explicitChoice()` after `exec()` to disambiguate dismissal from a
    deliberate Don't Allow click — both return QDialog.Rejected by themselves.
    """

    def __init__(self, parent=None, app_name: str = 'Baram', cancellable: bool = False):
        super().__init__(parent)
        self._appName = app_name
        self._cancellable = cancellable
        self._explicitChoice = None  # None=dismissed, True=allow, False=deny

        self.setWindowTitle(self.tr('Help Improve {0}').format(app_name))
        self.setModal(True)
        self.setMinimumSize(640, 600)
        if not cancellable:
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._buildUi()

    def explicitChoice(self):
        """True if user clicked Allow, False if Don't Allow, None if dismissed."""
        return self._explicitChoice

    def _buildUi(self):
        layout = QVBoxLayout(self)

        title = QLabel(self.tr('Help Improve {0}').format(self._appName), self)
        title.setStyleSheet('font-size: 14pt; font-weight: bold;')
        layout.addWidget(title)

        intro = QLabel(self.tr(
            '{0} can send anonymous usage data and error reports so we can find bugs '
            'and improve the product. Your participation is optional. You can change '
            'your choice at any time in Help → Privacy Settings.'
        ).format(self._appName), self)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        body = QTextBrowser(self)
        body.setOpenExternalLinks(True)
        body.setHtml(self._noticeHtml())
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(body, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        self._denyButton = QPushButton(self.tr("Don't Allow"), self)
        self._allowButton = QPushButton(self.tr('Allow'), self)
        for b in (self._denyButton, self._allowButton):
            b.setDefault(False)
            b.setAutoDefault(False)

        buttons.addWidget(self._denyButton)
        buttons.addWidget(self._allowButton)
        layout.addLayout(buttons)

        self._denyButton.clicked.connect(self._onDeny)
        self._allowButton.clicked.connect(self._onAllow)

    def _onAllow(self):
        self._explicitChoice = True
        self.done(QDialog.DialogCode.Accepted)

    def _onDeny(self):
        self._explicitChoice = False
        self.done(QDialog.DialogCode.Rejected)

    def _noticeHtml(self) -> str:
        return self.tr("""\
<h3>What is collected</h3>
<ul>
  <li>App version, operating system, language, and approximate geographic location (country / region, derived from your IP)</li>
  <li>Anonymous usage events: which features are opened, session duration, basic UI interactions</li>
  <li>Crash and error details: error type, message, stack trace, and the app state at the time of the error</li>
  <li>A randomly generated anonymous identifier stored on your computer (not linked to your name or account)</li>
</ul>

<h3>What is NOT collected</h3>
<ul>
  <li>Your name, email address, or other contact information</li>
  <li>Your project files, CAD geometry, mesh data, or simulation results</li>
  <li>File paths, file contents, or any data from outside the application</li>
  <li>Your IP address &mdash; it is used momentarily on our analytics provider's server to derive your country/region and is then discarded; the raw IP is not stored</li>
</ul>

<h3>Who processes the data</h3>
<p>Analytics and error reports are processed by <b>PostHog Inc.</b> (<a href="https://posthog.com">posthog.com</a>) acting as our data processor. Data is hosted on PostHog's EU infrastructure under a Data Processing Agreement (Art. 28 GDPR).</p>

<h3>Your rights &mdash; EU / UK / EEA</h3>
<p>Processing is based on your consent (Art. 6(1)(a) GDPR / UK GDPR). You may withdraw consent at any time without affecting the lawfulness of processing performed before withdrawal. You have the right to access, rectify, restrict, port, or erase your data, and to lodge a complaint with your supervisory authority. Contact: <a href="mailto:privacy@nextfoam.com">privacy@nextfoam.com</a>.</p>

<h3>Your rights &mdash; United States (CCPA / CPRA and similar state laws)</h3>
<p>You have the right to know what personal information is collected, to request its deletion, to correct inaccurate information, and to opt out of any "sale" or "sharing" of personal information. <b>We do not sell or share your personal information.</b></p>

<h3>Other jurisdictions</h3>
<p>Equivalent rights apply under LGPD (Brazil), PIPEDA (Canada), APPI (Japan), PIPA (Korea), POPIA (South Africa), and similar laws. Use the contact above to exercise them.</p>

<h3>Children</h3>
<p>This software is not intended for users under 16. We do not knowingly collect data from children.</p>

<h3>Retention</h3>
<p>Anonymous usage data is retained for up to <b>12 months</b>. Crash reports are retained for up to <b>24 months</b>. You may request earlier deletion at any time using the contact above.</p>
""")

    def reject(self):
        # In non-cancellable mode, block all paths to dismiss the dialog
        # without an explicit Allow / Don't Allow click.
        if self._cancellable:
            super().reject()

    def closeEvent(self, event):
        if self._cancellable:
            super().closeEvent(event)
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and not self._cancellable:
            event.ignore()
            return
        super().keyPressEvent(event)
