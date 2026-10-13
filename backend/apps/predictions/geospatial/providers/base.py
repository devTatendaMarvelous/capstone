"""Base class for geospatial environmental data providers."""

from __future__ import annotations

import abc
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class BaseProvider(abc.ABC):
    """Abstract interface for external geospatial environmental data providers."""

    name: str = "base"
    default_timeout: int = 15
    user_agent: str = "SmartCrop/1.0 (academic; Macheke maize yield prediction)"

    def _http_get_json(self, url: str, timeout: int | None = None) -> tuple[int, dict[str, Any]]:
        """Perform HTTP GET request and return parsed JSON."""
        timeout_val = timeout or self.default_timeout
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_val) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                return status_code, json.loads(body)
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP error %s when accessing %s: %s", exc.code, url[:120], exc)
            raise
        except Exception as exc:
            logger.warning("Network or timeout error accessing %s: %s", url[:120], exc)
            raise

    @abc.abstractmethod
    def acquire(self, latitude: float, longitude: float, season_year: int) -> dict[str, Any]:
        """Acquire environmental variables, returning measurements, provenance, and quality warnings.

        Returns:
            {
                "data": {param_name: float_value},
                "provenance": {...},
                "warnings": [str],
                "missing": [str],
            }
        """
        raise NotImplementedError
