#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

_mutex = Lock()


class Analytics:
    """Process-wide singleton for PostHog analytics + consent.

    Lifecycle:
        Analytics().configure(app_name, app_version, config_dir)  # called once from main()
        Analytics().ensureConsent()                   # first-launch dialog
        Analytics().init()                            # spin up PostHog; auto-fires APP_LAUNCHED
        Analytics().capture(event, properties)        # fire-and-forget
        Analytics().shutdown(final=True)              # at process exit; auto-fires APP_CLOSED

    Every public method silently no-ops when the singleton is not configured
    or the user has not consented, so call sites need no guards.

    Default properties (`app`, `app_version`, `$session_id`, `platform`) are merged into every
    captured event automatically — callers only need to supply event-specific
    context.
    """

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(Analytics, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            self._initialized = True

        self._app_name: Optional[str] = None
        self._app_version: Optional[str] = None
        self._config_dir: Optional[Path] = None
        self._distinct_id_file: Optional[Path] = None
        self._session_id: Optional[str] = None
        self._api_key: str = ''
        self._host: str = ''
        self._posthog = None
        self._consent = None
        self._launch_captured = False

    def configure(self, app_name: str, app_version: str, config_dir: Path) -> None:
        """Bind the singleton to an app's name, version, and config dir.

        Silently no-ops when `analytics/_config.py` is absent or empty — that's
        the signal that this build (e.g. dev source tree, OEM variant without
        keys) doesn't ship analytics. Every other method then no-ops via the
        `configured` guard, so no consent dialog appears either.
        """
        api_key, host = self._loadConfig()
        if not api_key or not host:
            return
        from .consent import AnalyticsConsent
        self._app_name = app_name
        self._app_version = app_version
        self._config_dir = Path(config_dir)
        self._distinct_id_file = self._config_dir / 'analytics_id'
        self._api_key = api_key
        self._host = host
        # One session per process launch — events from this run group together
        # in PostHog's session view.
        self._session_id = str(uuid.uuid4())
        self._consent = AnalyticsConsent(self._config_dir)

    @property
    def configured(self) -> bool:
        return self._app_name is not None

    @property
    def consented(self) -> bool:
        return self.configured and self._consent is not None and self._consent.getConsent()

    def ensureConsent(self, parent=None) -> bool:
        """First-launch path: show the consent dialog if no decision exists.
        Returns the current consent value (False if not configured).
        """
        if not self.configured or self._consent is None or self._app_name is None:
            return False
        return self._consent.ensureDecision(self._app_name, parent=parent)

    def editConsent(self, parent=None) -> Optional[bool]:
        """Settings path: show a cancellable consent dialog. Reconfigures the
        PostHog client based on the new decision. Returns the new value, or
        None if dismissed without change.
        """
        if not self.configured or self._consent is None or self._app_name is None:
            return None
        new_consent = self._consent.editDecision(self._app_name, parent=parent)
        if new_consent is None:
            return None
        if new_consent:
            self.init()
        else:
            self.shutdown()
        return new_consent

    def init(self) -> None:
        from .events import APP_LAUNCHED
        if not self.consented or self._posthog is not None:
            return
        try:
            from posthog import Posthog
            self._posthog = Posthog(self._api_key, host=self._host, disable_geoip=False)
        except Exception:
            logger.debug('PostHog analytics not available', exc_info=True)

        # Fire APP_LAUNCHED once per process, on the first successful init.
        # Subsequent inits (e.g. after revoke→re-allow via Privacy Settings)
        # don't re-fire — the app didn't relaunch.
        if self._posthog is not None and not self._launch_captured:
            self.capture(APP_LAUNCHED)
            self._launch_captured = True

    def capture(self, event: str, properties: Optional[dict] = None) -> None:
        if not self.consented or self._posthog is None:
            return
        try:
            self._posthog.capture(
                event,
                distinct_id=self._getDistinctId(),
                properties=self._mergeProperties(properties))
            self._posthog.flush()
        except Exception:
            logger.debug('PostHog capture failed', exc_info=True)

    def captureException(self, exception: BaseException, properties: Optional[dict] = None) -> None:
        if not self.consented or self._posthog is None:
            return
        try:
            distinct_id = self._getDistinctId()
            merged = self._mergeProperties(properties)
            if hasattr(self._posthog, 'capture_exception'):
                self._posthog.capture_exception(
                    exception, distinct_id=distinct_id, properties=merged)
                return
            import traceback
            tb = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__))
            merged.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'exception_traceback': tb,
            })
            self._posthog.capture('$exception', distinct_id=distinct_id, properties=merged)
        except Exception:
            logger.debug('PostHog exception capture failed', exc_info=True)

    def shutdown(self, final: bool = False) -> None:
        """Stop the PostHog client.

        `final=True` indicates this is the process-exit shutdown and fires an
        APP_CLOSED event before tearing down. The default `final=False` is for
        in-process shutdowns (e.g., user revoked consent via Privacy Settings)
        where the app is still running.
        """
        from .events import APP_CLOSED
        if self._posthog is None:
            return
        if final and self._launch_captured:
            self.capture(APP_CLOSED)
        try:
            self._posthog.shutdown()
        except Exception:
            pass
        self._posthog = None

    def _mergeProperties(self, properties: Optional[dict]) -> dict:
        merged = {
            'app': self._app_name,
            'app_version': self._app_version,
            '$session_id': self._session_id,
            'platform': sys.platform,
        }
        if properties:
            merged.update(properties)
        return merged

    @staticmethod
    def _loadConfig():
        try:
            from . import _config as cfg  # pyright: ignore[reportMissingImports]
            return getattr(cfg, 'POSTHOG_API_KEY', ''), getattr(cfg, 'POSTHOG_HOST', '')
        except ImportError:
            return '', ''

    def _getDistinctId(self) -> str:
        if self._distinct_id_file is None:
            return 'anonymous'
        try:
            if self._distinct_id_file.exists():
                return self._distinct_id_file.read_text().strip()
            distinct_id = str(uuid.uuid4())
            self._distinct_id_file.parent.mkdir(parents=True, exist_ok=True)
            self._distinct_id_file.write_text(distinct_id)
            return distinct_id
        except Exception:
            return 'anonymous'
