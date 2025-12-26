import logging
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
        regions: object | None = None,
        bounded: object | None = None,
    ) -> None:
        self.base_url = base_url
        self.limit = limit
        self.timeout = timeout
        self.user_agent = user_agent
        self.regions = regions or {}
        self.bounded = bounded

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
            regions=getattr(nominatim, "regions", None) or {},
            bounded=getattr(nominatim, "bounded", None),
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
        viewboxes = self._get_viewboxes()
        async with aiohttp.ClientSession() as session:
            if viewboxes:
                for viewbox in viewboxes:
                    regional_params = dict(params)
                    regional_params["viewbox"] = viewbox
                    if self.bounded:
                        regional_params["bounded"] = 1
                    data = await self._request(session, regional_params, headers)
                    for item in data:
                        self._add_suggestion(item, suggestions, index_by_name)
                        if len(suggestions) >= self.limit:
                            return suggestions
            else:
                data = await self._request(session, params, headers)
                for item in data:
                    self._add_suggestion(item, suggestions, index_by_name)
                    if len(suggestions) >= self.limit:
                        return suggestions

        return suggestions

    def _get_viewboxes(self) -> list[str]:
        if not self.regions:
            return []

        region_map = self.regions
        if isinstance(region_map, dict):
            candidates = region_map.values()
        elif isinstance(region_map, (list, tuple)):
            candidates = region_map
        else:
            candidates = [region_map]

        viewboxes = []
        for candidate in candidates:
            viewbox = self._normalize_viewbox(candidate)
            if viewbox:
                viewboxes.append(viewbox)

        if not viewboxes:
            logger.warning("Geocoder regions are configured but no valid viewboxes found")
        return viewboxes

    def _normalize_viewbox(self, viewbox: object) -> str | None:
        if isinstance(viewbox, (list, tuple)):
            return ",".join(str(value) for value in viewbox)
        if viewbox is None:
            return None
        viewbox = str(viewbox).strip()
        return viewbox or None

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
        }

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
