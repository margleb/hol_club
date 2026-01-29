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
        allowed_cities: Iterable[str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.results_limit = results_limit
        self.timeout_seconds = timeout_seconds
        self.allowed_cities = [
            str(city).strip()
            for city in (allowed_cities or [])
            if str(city).strip()
        ]

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
        if not self.allowed_cities:
            return suggestions
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
            address = self._build_short_address(metadata)
            if not address:
                address = (
                    (metadata.get("Address") or {}).get("formatted")
                    or metadata.get("text")
                    or geo_object.get("name")
                )
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
                is_moscow=self._is_allowed_city(metadata),
                has_house_number=self._has_house_number(metadata),
            )

    def _build_short_address(self, metadata: dict[str, Any]) -> str:
        address_meta = metadata.get("Address") or {}
        components = address_meta.get("Components") or []
        city = self._get_component_name(components, {"locality"})
        street = self._get_component_name(components, {"street", "thoroughfare"})
        house = self._get_component_name(components, {"house"})

        address_details = metadata.get("AddressDetails") or {}
        if not city:
            city = self._get_address_details_locality(address_details)
        if not street:
            street = self._get_address_details_street(address_details)
        if not house:
            house = self._get_address_details_house(address_details)

        parts = [city, street, house]
        return ", ".join(part for part in parts if part)

    def _get_component_name(
        self,
        components: Iterable[dict[str, Any]],
        kinds: set[str],
    ) -> str:
        for component in components:
            kind = str(component.get("kind") or "").lower().strip()
            if kind not in kinds:
                continue
            name = str(component.get("name") or "").strip()
            if name:
                return name
        return ""

    def _get_address_details_locality(self, details: dict[str, Any]) -> str:
        country = details.get("Country") or {}
        admin_area = country.get("AdministrativeArea") or {}
        locality = admin_area.get("Locality") or {}
        if not locality:
            locality = (
                admin_area.get("SubAdministrativeArea", {})
                .get("Locality", {})
            ) or {}
        return str(locality.get("LocalityName") or "").strip()

    def _get_address_details_street(self, details: dict[str, Any]) -> str:
        locality = self._get_address_details_locality_block(details)
        thoroughfare = locality.get("Thoroughfare") or {}
        return str(thoroughfare.get("ThoroughfareName") or "").strip()

    def _get_address_details_house(self, details: dict[str, Any]) -> str:
        locality = self._get_address_details_locality_block(details)
        thoroughfare = locality.get("Thoroughfare") or {}
        premise = thoroughfare.get("Premise") or {}
        return str(premise.get("PremiseNumber") or "").strip()

    def _get_address_details_locality_block(
        self,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        country = details.get("Country") or {}
        admin_area = country.get("AdministrativeArea") or {}
        locality = admin_area.get("Locality") or {}
        if not locality:
            locality = (
                admin_area.get("SubAdministrativeArea", {})
                .get("Locality", {})
            ) or {}
        return locality

    def _is_allowed_city(self, metadata: dict[str, Any]) -> bool:
        if not self.allowed_cities:
            return True

        address_meta = metadata.get("Address") or {}
        components = address_meta.get("Components") or []

        for component in components:
            name = str(component.get("name") or "")
            kind = str(component.get("kind") or "")
            if self._is_allowed_city_component(name=name, kind=kind):
                return True

        formatted = str(
            address_meta.get("formatted")
            or metadata.get("text")
            or ""
        )
        return self._text_mentions_city(formatted)

    def _is_allowed_city_component(self, *, name: str, kind: str) -> bool:
        normalized_name = name.replace("ё", "е").lower().strip()
        if kind not in {"locality", "province"}:
            return False
        return self._text_mentions_city(normalized_name)

    def _text_mentions_city(self, text: str) -> bool:
        tokens = self._tokenize(text)
        if not tokens:
            return False

        if {"область", "oblast", "obl"}.intersection(tokens):
            return False

        for city_tokens in self._allowed_city_tokens():
            if city_tokens and city_tokens.issubset(tokens):
                return True
        return False

    def _allowed_city_tokens(self) -> list[set[str]]:
        return [
            self._tokenize(city)
            for city in self.allowed_cities
            if self._tokenize(city)
        ]

    def _tokenize(self, text: str) -> set[str]:
        cleaned = text.replace("ё", "е").lower()
        return {token for token in re.split(r"[^a-zа-я0-9]+", cleaned) if token}

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
