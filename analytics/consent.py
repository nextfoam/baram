#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Bump whenever the *content* of the privacy notice changes materially
# (new data category, new processor, changed retention). A change here forces
# users to re-consent on the next launch.
CONSENT_VERSION = 1


class AnalyticsConsent:
    """Storage-only consent tracker.

    Each Baram application owns its own instance under its own config dir, so
    consent is recorded independently per app even when they're installed
    together.
    """

    def __init__(self, config_dir: Path):
        self._file = Path(config_dir) / 'analytics_consent.json'

    def hasDecision(self) -> bool:
        return self._load() is not None

    def getConsent(self) -> bool:
        data = self._load()
        return bool(data and data.get('consent', False))

    def setConsent(self, consent: bool) -> None:
        data = {
            'consent': bool(consent),
            'version': CONSENT_VERSION,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(json.dumps(data, indent=2))
        except Exception:
            logger.debug('Failed to save analytics consent', exc_info=True)

    def ensureDecision(self, app_name: str, parent=None) -> bool:
        """Show the consent dialog if no decision has been recorded yet.

        Returns the current consent value (True if user allowed, False otherwise).
        Safe to call before the main window exists — the dialog runs its own
        modal event loop. The dialog blocks dismissal so the user must click
        Allow or Don't Allow.
        """
        if not self.hasDecision():
            from .consent_dialog import ConsentDialog
            dialog = ConsentDialog(parent=parent, app_name=app_name)
            dialog.exec()
            # In non-cancellable mode explicitChoice() is always True or False.
            self.setConsent(bool(dialog.explicitChoice()))
        return self.getConsent()

    def editDecision(self, app_name: str, parent=None):
        """Show the consent dialog from a settings menu so the user can change
        a previously recorded decision.

        Returns the new consent value (bool) if changed, or None if the user
        dismissed the dialog without making a choice.
        """
        from .consent_dialog import ConsentDialog
        dialog = ConsentDialog(parent=parent, app_name=app_name, cancellable=True)
        dialog.exec()
        choice = dialog.explicitChoice()
        if choice is None:
            return None
        self.setConsent(choice)
        return choice

    def _load(self) -> Optional[dict]:
        try:
            if not self._file.exists():
                return None
            data = json.loads(self._file.read_text())
            if data.get('version') != CONSENT_VERSION:
                return None
            return data
        except Exception:
            logger.debug('Failed to load analytics consent', exc_info=True)
            return None
