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
    participation_label = (
        i18n.partner.event.participation.paid()
        if is_paid
        else i18n.partner.event.participation.free()
    )

    lines: list[str] = [
        f"<b>{name}</b>",
        i18n.partner.event.label.datetime(value=date_time),
        i18n.partner.event.label.address(value=address),
    ]

    if description:
        lines.append("")
        lines.append(description)

    lines.append("")
    lines.append(i18n.partner.event.label.participation(value=participation_label))

    if is_paid and price:
        lines.append(i18n.partner.event.label.price(value=price))

    if age_group:
        lines.append(i18n.partner.event.label.age(value=age_group))

    return "\n".join(lines).strip()


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
