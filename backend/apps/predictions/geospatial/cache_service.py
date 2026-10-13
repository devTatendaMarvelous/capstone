"""Caching service for acquired geospatial environmental records."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from django.utils import timezone as dj_timezone

logger = logging.getLogger(__name__)


def make_grid_cell(latitude: float, longitude: float, resolution: float = 0.05) -> str:
    """Format coordinates into a canonical spatial grid cell key (default ~5 km)."""
    grid_lat = round(round(latitude / resolution) * resolution, 4)
    grid_lon = round(round(longitude / resolution) * resolution, 4)
    return f"{grid_lat:.4f},{grid_lon:.4f}"


def make_cache_key(provider: str, grid_cell: str, date_range: str, parameters: list[str]) -> str:
    """Generate a deterministic cache key."""
    params_key = ",".join(sorted(parameters))
    raw = f"{provider}:{grid_cell}:{date_range}:{params_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


class GeospatialCacheService:
    """Query and manage cached geospatial payloads."""

    @classmethod
    def get(cls, provider: str, grid_cell: str, date_range: str, parameters: list[str]) -> dict[str, Any] | None:
        """Lookup cached entry if present and not expired."""
        from apps.predictions.models import EnvironmentalCache

        key = make_cache_key(provider, grid_cell, date_range, parameters)
        try:
            entry = EnvironmentalCache.objects.filter(cache_key=key).first()
            if entry is None:
                return None
            if entry.expires_at and entry.expires_at < dj_timezone.now():
                logger.info("Cache entry expired for %s", key)
                return None
            return {
                "data": entry.payload,
                "provenance": entry.provenance,
                "cached": True,
                "cached_at": entry.created_at.isoformat(),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache lookup error for %s: %s", key, exc)
            return None

    @classmethod
    def set(
        cls,
        provider: str,
        grid_cell: str,
        date_range: str,
        parameters: list[str],
        payload: dict[str, Any],
        provenance: dict[str, Any],
        ttl_days: int = 14,
    ) -> None:
        """Store environmental entry in the persistent cache."""
        from apps.predictions.models import EnvironmentalCache

        key = make_cache_key(provider, grid_cell, date_range, parameters)
        expires = dj_timezone.now() + timedelta(days=ttl_days)
        try:
            EnvironmentalCache.objects.update_or_create(
                cache_key=key,
                defaults={
                    "provider": provider,
                    "grid_cell": grid_cell,
                    "date_range": date_range,
                    "parameters": sorted(parameters),
                    "payload": payload,
                    "provenance": provenance,
                    "expires_at": expires,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to store cache entry %s: %s", key, exc)
