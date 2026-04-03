from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
EVENT_DATETIME_INPUT_FORMATS = (
    "%Y.%m.%d %H:%M",
    "%d.%m.%Y %H:%M",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y %H:%M",
    "%Y/%m/%d %H:%M",
    "%d/%m/%Y %H:%M",
)
EVENT_DATETIME_DISPLAY_FORMAT = "%d.%m.%Y %H:%M"
EVENT_DATETIME_TOPIC_FORMAT = "%d.%m %H:%M"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_moscow() -> datetime:
    return datetime.now(MOSCOW_TZ)


def parse_event_datetime_input(value: str) -> datetime:
    raw_value = value.strip().replace("T", " ")
    for date_format in EVENT_DATETIME_INPUT_FORMATS:
        try:
            naive = datetime.strptime(raw_value, date_format)
        except ValueError:
            continue
        return naive.replace(tzinfo=MOSCOW_TZ)
    raise ValueError(f"Unsupported event datetime format: {value}")


def coerce_event_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        raw_value = str(value).strip()
        if not raw_value:
            return None
        try:
            result = datetime.fromisoformat(raw_value)
        except ValueError:
            try:
                result = parse_event_datetime_input(raw_value)
            except ValueError:
                return None

    if result.tzinfo is None:
        return result.replace(tzinfo=MOSCOW_TZ)
    return result


def format_event_datetime(value: object) -> str:
    event_datetime = coerce_event_datetime(value)
    if event_datetime is None:
        return str(value or "")
    localized = event_datetime.astimezone(MOSCOW_TZ)
    return localized.strftime(EVENT_DATETIME_DISPLAY_FORMAT)


def format_event_datetime_compact(value: object) -> str:
    event_datetime = coerce_event_datetime(value)
    if event_datetime is None:
        return str(value or "")
    localized = event_datetime.astimezone(MOSCOW_TZ)
    if localized.year != now_moscow().year:
        return localized.strftime(EVENT_DATETIME_DISPLAY_FORMAT)
    return localized.strftime(EVENT_DATETIME_TOPIC_FORMAT)


def is_event_past(value: object, *, reference: datetime | None = None) -> bool:
    event_datetime = coerce_event_datetime(value)
    if event_datetime is None:
        return False

    current_time = reference or now_utc()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    return event_datetime.astimezone(timezone.utc) < current_time.astimezone(
        timezone.utc
    )


def compute_private_chat_delete_at(value: object) -> datetime | None:
    event_datetime = coerce_event_datetime(value)
    if event_datetime is None:
        return None

    return event_datetime.astimezone(timezone.utc) + timedelta(hours=24)
