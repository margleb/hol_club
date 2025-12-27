from urllib.parse import quote_plus

from fluentogram import TranslatorRunner

CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096


def _truncate_text(value: str, max_len: int) -> str:
    if max_len <= 0:
        return ""
    if len(value) <= max_len:
        return value
    if max_len <= 3:
        return value[:max_len]
    return value[: max_len - 3].rstrip() + "..."


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _build_address_link(address: str) -> str:
    query = quote_plus(address.strip())
    return f"https://yandex.ru/maps/?text={query}"


def _render_event_text(
    *,
    name: str,
    date_time: str,
    address: str,
    description: str,
    is_paid: bool,
    price: str | None,
    age_group: str | None,
    i18n: TranslatorRunner,
) -> str:
    participation_value = (
        price if is_paid and price else i18n.partner.event.participation.free()
    )
    datetime_line = i18n.partner.event.label.datetime(value=date_time)
    address_line = i18n.partner.event.label.address(
        value=f'<a href="{_build_address_link(address)}">{address}</a>',
    )
    participation_line = i18n.partner.event.label.participation(
        value=participation_value
    )
    age_block = (
        f"{i18n.partner.event.label.age(value=age_group)}"
        if age_group
        else ""
    )
    description_block = f"{description}" if description else ""

    return i18n.partner.event.text.template(
        name=name,
        datetime=datetime_line,
        address=address_line,
        participation=participation_line,
        description_block=description_block,
        age_block=age_block,
    )


def build_event_text(
    data: dict,
    i18n: TranslatorRunner,
    *,
    max_length: int | None = None,
) -> tuple[str, bool]:
    raw_name = data.get("name") or ""
    raw_date_time = data.get("datetime") or ""
    raw_address = data.get("address") or ""
    raw_description = data.get("description") or ""
    is_paid = bool(data.get("is_paid"))
    raw_price = data.get("price")
    raw_age_group = data.get("age_group")

    def render(description: str, address: str) -> str:
        return _render_event_text(
            name=_escape_html(raw_name),
            date_time=_escape_html(raw_date_time),
            address=_escape_html(address),
            description=_escape_html(description),
            is_paid=is_paid,
            price=_escape_html(raw_price) if raw_price else None,
            age_group=_escape_html(raw_age_group) if raw_age_group else None,
            i18n=i18n,
        )

    text = render(raw_description, raw_address)

    if not max_length or len(text) <= max_length:
        return text, False

    trimmed = True
    over_by = len(text) - max_length
    raw_description = _truncate_text(raw_description, len(raw_description) - over_by)

    text = render(raw_description, raw_address)

    if len(text) > max_length and raw_address:
        over_by = len(text) - max_length
        raw_address = _truncate_text(raw_address, len(raw_address) - over_by)
        text = render(raw_description, raw_address)

    if len(text) > max_length:
        text = text[:max_length].rstrip()

    return text, trimmed
