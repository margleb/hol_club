from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
EVENT_DATETIME_INPUT_FORMAT = "%Y.%m.%d %H:%M"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_moscow() -> datetime:
    return datetime.now(MOSCOW_TZ)


def parse_event_datetime_input(value: str) -> datetime:
    naive = datetime.strptime(value.strip(), EVENT_DATETIME_INPUT_FORMAT)
    return naive.replace(tzinfo=MOSCOW_TZ)


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
    return event_datetime.astimezone(MOSCOW_TZ).strftime(EVENT_DATETIME_INPUT_FORMAT)


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

    local_event_datetime = event_datetime.astimezone(MOSCOW_TZ)
    next_day = local_event_datetime.date() + timedelta(days=1)
    delete_at_local = datetime.combine(next_day, time(hour=3), tzinfo=MOSCOW_TZ)
    return delete_at_local.astimezone(timezone.utc)
