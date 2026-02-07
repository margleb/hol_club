from urllib.parse import quote_plus

from fluentogram import TranslatorRunner

from app.bot.dialogs.events.constants import EVENT_AGE_GROUP_ALL

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
) -> str:
    raw_name = data.get("name") or ""
    raw_date_time = data.get("datetime") or ""
    raw_address = data.get("address") or ""
    raw_description = data.get("description") or ""
    is_paid = bool(data.get("is_paid"))
    raw_price = data.get("price")
    raw_age_group = data.get("age_group")
    display_age_group = (
        i18n.partner.event.age.everyone()
        if raw_age_group == EVENT_AGE_GROUP_ALL
        else raw_age_group
    )

    def render(description: str, address: str) -> str:
        return _render_event_text(
            name=_escape_html(raw_name),
            date_time=_escape_html(raw_date_time),
            address=_escape_html(address),
            description=_escape_html(description),
            is_paid=is_paid,
            price=_escape_html(raw_price) if raw_price else None,
            age_group=_escape_html(display_age_group) if display_age_group else None,
            i18n=i18n,
        )

    return render(raw_description, raw_address)


def build_event_topic_name(event_datetime: str, event_name: str) -> str:
    date_value = (event_datetime or "").strip()
    name = (event_name or "").strip()
    if date_value and name:
        base = f"{date_value} - {name}"
    else:
        base = date_value or name

    max_len = 128
    if len(base) <= max_len:
        return base

    ellipsis = "..."
    if date_value and name:
        budget = max_len - len(date_value) - len(" - ") - len(ellipsis)
        if budget > 0:
            return f"{date_value} - {name[:budget]}{ellipsis}"

    trimmed = base[: max_len - len(ellipsis)]
    return f"{trimmed}{ellipsis}"
