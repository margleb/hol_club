import logging
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class NominatimGeocoder:
    def __init__(
        self,
        base_url: str | None,
        *,
        limit: int = 5,
        timeout: float = 7,
        user_agent: str = "hol_club_bot",
        allowed_cities: object | None = None,
    ) -> None:
        self.base_url = base_url
        self.limit = limit
        self.timeout = timeout
        self.user_agent = user_agent
        self.allowed_cities = self._normalize_allowed_cities(allowed_cities)

    @classmethod
    def from_settings(cls, settings: Any) -> "NominatimGeocoder":
        nominatim = getattr(settings, "nominatim", None)
        if not nominatim:
            return cls(None)
        return cls(
            getattr(nominatim, "url", None),
            limit=int(getattr(nominatim, "limit", 5) or 5),
            timeout=float(getattr(nominatim, "timeout", 7) or 7),
            user_agent=getattr(nominatim, "user_agent", None) or "hol_club_bot",
            allowed_cities=getattr(settings, "geocoding", None)
            and getattr(settings.geocoding, "allowed_cities", None),
        )

    async def search(
        self,
        query: str,
        locale: str | None,
    ) -> list[dict[str, str | bool]]:
        if not self.base_url:
            logger.warning("Geocoder URL is not set")
            return []

        params = {
            "q": query,
            "format": "json",
            "limit": self.limit,
            "addressdetails": 1,
        }
        if locale:
            params["accept-language"] = locale

        headers = {"User-Agent": self.user_agent}

        suggestions: list[dict[str, str | bool]] = []
        index_by_name: dict[str, int] = {}
        async with aiohttp.ClientSession() as session:
            data = await self._request(session, params, headers)
            for item in data:
                self._add_suggestion(item, suggestions, index_by_name)
                if len(suggestions) >= self.limit:
                    return suggestions

        if not self.allowed_cities:
            return suggestions
        return [item for item in suggestions if item.get("is_moscow")]

    async def _request(
        self,
        session: aiohttp.ClientSession,
        params: dict[str, Any],
        headers: dict[str, str],
    ) -> list[dict[str, Any]]:
        try:
            async with session.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            ) as response:
                if response.status != 200:
                    return []
                data = await response.json()
        except Exception as exc:
            logger.warning("Geocoder request failed: %s", exc)
            return []

        if not isinstance(data, list):
            return []
        return data

    def _build_suggestion(self, item: dict[str, Any]) -> dict[str, str | bool] | None:
        display_name = item.get("display_name")
        if not display_name:
            return None

        address = item.get("address")
        has_house_number = bool(
            isinstance(address, dict) and address.get("house_number")
        )
        return {
            "display_name": display_name,
            "has_house_number": has_house_number,
            "is_moscow": self._is_moscow(address, display_name),
        }

    def _is_moscow(self, address: dict[str, Any] | None, display_name: str) -> bool:
        if not self.allowed_cities:
            return True
        if isinstance(address, dict):
            for key in (
                "city",
                "town",
                "village",
                "municipality",
                "state",
                "county",
                "region",
            ):
                value = address.get(key)
                if value and self._text_mentions_city(str(value)):
                    return True
        return self._text_mentions_city(display_name)

    def _text_mentions_city(self, text: str) -> bool:
        tokens = self._tokenize(text)
        if not tokens:
            return False

        if {"область", "oblast", "obl"}.intersection(tokens):
            return False

        for city_tokens in self.allowed_cities:
            if city_tokens and city_tokens.issubset(tokens):
                return True
        return False

    def _tokenize(self, text: str) -> set[str]:
        cleaned = text.replace("ё", "е").lower()
        return {token for token in re.split(r"[^a-zа-я0-9]+", cleaned) if token}

    def _normalize_allowed_cities(
        self,
        allowed_cities: object | None,
    ) -> list[set[str]]:
        if not allowed_cities:
            return []
        if isinstance(allowed_cities, (list, tuple, set)):
            candidates = allowed_cities
        else:
            candidates = [allowed_cities]

        return [
            tokens
            for city in candidates
            if (tokens := self._tokenize(str(city)))
        ]

    def _add_suggestion(
        self,
        item: dict[str, Any],
        suggestions: list[dict[str, str | bool]],
        index_by_name: dict[str, int],
    ) -> None:
        suggestion = self._build_suggestion(item)
        if not suggestion:
            return

        display_name = suggestion["display_name"]
        existing_index = index_by_name.get(display_name)
        if existing_index is None:
            suggestions.append(suggestion)
            index_by_name[display_name] = len(suggestions) - 1
            return

        if suggestion["has_house_number"] and not suggestions[existing_index][
            "has_house_number"
        ]:
            suggestions[existing_index]["has_house_number"] = True
