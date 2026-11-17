#!/usr/bin/env python3
"""Reject the retired historical binary import route before reading any payload."""
raise SystemExit('Historical component import is retired. Use the pinned source build; no binary fallback is allowed.')
