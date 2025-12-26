import logging
from typing import Any

from app.services.geocoders.nominatim_geocoder import NominatimGeocoder
from app.services.geocoders.yandex_geocoder import YandexGeocoder

logger = logging.getLogger(__name__)


def _get_provider(settings: Any) -> str:
    provider = str(settings.get("geocoder_provider") or "nominatim").strip().lower()
    if provider in {"yandex"}:
        return "yandex"
    if provider in {"nominatim", "osm", "openstreetmap"}:
        return "nominatim"
    logger.warning("Unknown geocoder provider: %s. Using nominatim.", provider)
    return "nominatim"


async def fetch_address_suggestions(
    query: str,
    locale: str | None,
    settings: Any,
) -> list[dict[str, str | bool]]:
    provider = _get_provider(settings)
    if provider == "yandex":
        return await _fetch_yandex_suggestions(query, settings)

    geocoder = NominatimGeocoder.from_settings(settings)
    return await geocoder.search(query, locale)


async def _fetch_yandex_suggestions(
    query: str,
    settings: Any,
) -> list[dict[str, str | bool]]:
    geocoding = getattr(settings, "geocoding", None)
    allowed_cities = getattr(geocoding, "allowed_cities", None) if geocoding else None
    results_limit = getattr(settings.yandex, "geocoder_results_limit", 5)
    timeout_seconds = getattr(settings.yandex, "geocoder_timeout_seconds", 10)
    try:
        results_limit = max(1, int(results_limit))
    except (TypeError, ValueError):
        results_limit = 5
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 10

    geocoder = YandexGeocoder(
        api_key=getattr(settings.yandex, "geocoder_api_key", ""),
        results_limit=results_limit,
        timeout_seconds=timeout_seconds,
        allowed_cities=allowed_cities,
    )

    try:
        suggestions = await geocoder.search(query)
    except ValueError:
        logger.exception("Yandex geocoder API key is not configured")
        return []
    except Exception:
        logger.exception("Failed to fetch locations from Yandex geocoder")
        return []

    prepared: list[dict[str, str | bool]] = []
    for suggestion in suggestions:
        prepared.append({
            "display_name": suggestion.address,
            "has_house_number": suggestion.has_house_number,
        })
    return prepared
