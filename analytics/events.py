#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Canonical event names for PostHog analytics.

Reference these constants instead of using string literals at call sites so
the set of tracked events is discoverable and renames are mechanical.
"""

APP_LAUNCHED = 'app_launched'
APP_CLOSED = 'app_closed'
EVENT_LOOP_ERROR = 'event_loop_error'
UI_SCALING_CHANGED = 'ui_scaling_changed'
