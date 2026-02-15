from urllib.parse import unquote


def _extract_start_payload(text: str | None) -> str | None:
    if not text:
        return None

    text = text.strip()

    if " " in text:
        _, payload = text.split(maxsplit=1)
        return payload.strip() or None

    if "?" in text:
        _, payload = text.split("?", 1)
        return payload.strip() or None

    return None


def _strip_payload_query_suffix(payload: str) -> str:
    # Ignore optional tracking params accidentally appended to start payload.
    payload = payload.split("?", 1)[0]
    payload = payload.split("&", 1)[0]
    return payload.strip()


def parse_general_start_payload(
    message_text: str | None,
) -> tuple[str, str, str] | None:
    payload = _extract_start_payload(message_text)
    if not payload:
        return None

    payload = unquote(payload.strip())
    if not payload:
        return None

    if payload.startswith("start="):
        payload = payload.split("=", 1)[1]

    payload = _strip_payload_query_suffix(payload)
    if not payload:
        return None

    left, sep, price = payload.rpartition("_")
    if not sep or not price:
        return None

    placement_date, sep, channel_username = left.partition("_")
    if not sep or not placement_date or not channel_username:
        return None

    if placement_date.isdigit():
        return None

    channel_username = channel_username.lstrip("@")
    if not channel_username:
        return None

    if (
        len(placement_date) > 32
        or len(channel_username) > 64
        or len(price) > 32
    ):
        return None

    return placement_date, channel_username, price
