import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable

import aiohttp
from aiohttp import ClientTimeout

logger = logging.getLogger(__name__)


@dataclass
class GeocodeSuggestion:
    address: str
    lat: float
    lon: float
    is_moscow: bool = False
    has_house_number: bool = False


class YandexGeocoder:
    base_url = "https://geocode-maps.yandex.ru/1.x"

    def __init__(
        self,
        api_key: str,
        *,
        results_limit: int = 5,
        timeout_seconds: int = 10,
    ) -> None:
        self.api_key = api_key
        self.results_limit = results_limit
        self.timeout_seconds = timeout_seconds

    async def search(self, query: str) -> list[GeocodeSuggestion]:
        if not self.api_key:
            raise ValueError("Yandex geocoder API key is not configured")

        params = {
            "apikey": self.api_key,
            "geocode": query,
            "format": "json",
            "results": self.results_limit,
        }

        timeout = ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        "Yandex geocoder returned non-200 status: %s",
                        response.status,
                    )
                    response.raise_for_status()
                payload = await response.json()

        suggestions = list(self._parse_response(payload))
        return [item for item in suggestions if item.is_moscow]

    def _parse_response(self, payload: dict[str, Any]) -> Iterable[GeocodeSuggestion]:
        collection = (
            payload.get("response", {})
            .get("GeoObjectCollection", {})
            .get("featureMember", [])
        )
        for member in collection:
            geo_object = member.get("GeoObject", {})
            metadata = (
                geo_object.get("metaDataProperty", {})
                .get("GeocoderMetaData", {})
            )
            address = metadata.get("text") or geo_object.get("name")
            position = geo_object.get("Point", {}).get("pos")
            if not address or not position:
                continue

            parts = position.split()
            if len(parts) < 2:
                continue

            try:
                lon, lat = map(float, parts[:2])
            except (TypeError, ValueError):
                continue

            yield GeocodeSuggestion(
                address=address,
                lat=lat,
                lon=lon,
                is_moscow=self._is_moscow(metadata),
                has_house_number=self._has_house_number(metadata),
            )

    def _is_moscow(self, metadata: dict[str, Any]) -> bool:
        address_meta = metadata.get("Address") or {}
        components = address_meta.get("Components") or []

        for component in components:
            name = str(component.get("name") or "")
            kind = str(component.get("kind") or "")
            if self._is_moscow_component(name=name, kind=kind):
                return True

        formatted = str(
            address_meta.get("formatted")
            or metadata.get("text")
            or ""
        )
        return self._text_mentions_moscow(formatted)

    def _is_moscow_component(self, *, name: str, kind: str) -> bool:
        normalized_name = name.replace("ё", "е").lower().strip()
        if kind not in {"locality", "province"}:
            return False

        exact_matches = {
            "москва",
            "город москва",
            "город федерального значения москва",
            "moscow",
            "moskva",
        }
        if normalized_name in exact_matches:
            return True

        if normalized_name.endswith(" москва"):
            return True

        if normalized_name.endswith(" moscow") or normalized_name.endswith(" moskva"):
            return True

        return False

    def _text_mentions_moscow(self, text: str) -> bool:
        cleaned = text.replace("ё", "е").lower()
        if not cleaned:
            return False

        tokens = {token for token in re.split(r"[^a-zа-я0-9]+", cleaned) if token}
        if not ({"москва", "moscow", "moskva"} & tokens):
            return False

        if {"область", "oblast", "obl"}.intersection(tokens):
            return False

        return True

    def _has_house_number(self, metadata: dict[str, Any]) -> bool:
        kind = str(metadata.get("kind") or "").lower().strip()
        if kind == "house":
            return True

        address_meta = metadata.get("Address") or {}
        components = address_meta.get("Components") or []
        for component in components:
            component_kind = str(component.get("kind") or "").lower().strip()
            name = str(component.get("name") or "").strip()
            if component_kind == "house" and name:
                return True

        address_details = metadata.get("AddressDetails") or {}
        country = address_details.get("Country") or {}
        admin_area = country.get("AdministrativeArea") or {}
        locality = admin_area.get("Locality") or {}
        if not locality:
            locality = (
                admin_area.get("SubAdministrativeArea", {})
                .get("Locality", {})
            ) or {}
        thoroughfare = locality.get("Thoroughfare") or {}
        premise = thoroughfare.get("Premise") or {}
        if premise.get("PremiseNumber"):
            return True

        return False
