import logging
from dataclasses import dataclass
import xml.etree.ElementTree as ET

import aiohttp

logger = logging.getLogger(__name__)

ADVCAKE_EXPORT_URL = "https://api.advcake.com/export/webmaster"


@dataclass(frozen=True)
class AdvCakeOrder:
    order_id: str | None
    status: int | None
    sub1: str | None
    click_id: str | None
    price: str | None
    date_change: str | None


def _strip_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_orders_xml(xml_text: str) -> list[AdvCakeOrder]:
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Failed to parse AdvCake XML: %s", exc)
        return []

    root_tag = _strip_tag(root.tag)
    items_node = root if root_tag == "items" else root.find(".//items")
    if items_node is None:
        logger.warning("AdvCake XML missing <items> root")
        return []

    orders: list[AdvCakeOrder] = []
    for item in list(items_node):
        if _strip_tag(item.tag) != "item":
            continue
        data: dict[str, str] = {}
        for child in list(item):
            data[_strip_tag(child.tag)] = (child.text or "").strip()
        status_raw = data.get("status") or data.get("status_id")
        status = int(status_raw) if status_raw and status_raw.isdigit() else None
        orders.append(
            AdvCakeOrder(
                order_id=data.get("order_id") or data.get("id"),
                status=status,
                sub1=data.get("sub1"),
                click_id=data.get("click_id"),
                price=data.get("price"),
                date_change=data.get("date_change") or data.get("updated_at"),
            )
        )
    return orders


async def fetch_orders(
    *,
    api_key: str,
    days: int = 2,
    timeout_seconds: int = 15,
) -> list[AdvCakeOrder]:
    if not api_key:
        return []
    url = f"{ADVCAKE_EXPORT_URL}/{api_key}"
    params = {"days": str(days)}
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                body = await response.text()
                logger.warning(
                    "AdvCake API error status=%s body=%s",
                    response.status,
                    body[:500],
                )
                return []
            xml_text = await response.text()
    return parse_orders_xml(xml_text)
