from dataclasses import dataclass
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.enums.event_registrations import EventRegistrationStatus
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.events import EventsModel
from app.infrastructure.database.models.users import UsersModel
from app.utils.datetime import is_event_past

EVENT_DIALOG_OPEN_CALLBACK = "event_dialog_open"
DIALOG_EVENT_ID_KEY = "selected_dialog_event_id"
DIALOG_PARTICIPANT_USER_ID_KEY = "selected_dialog_participant_user_id"

PARTICIPANT_ALLOWED_STATUSES = {
    EventRegistrationStatus.CONFIRMED,
    EventRegistrationStatus.ATTENDED_CONFIRMED,
}
ORGANIZER_ALLOWED_STATUSES = {
    EventRegistrationStatus.PAID_CONFIRM_PENDING,
    EventRegistrationStatus.CONFIRMED,
    EventRegistrationStatus.ATTENDED_CONFIRMED,
}


@dataclass(frozen=True)
class EventDialogContext:
    event: EventsModel
    participant_user_id: int
    participant_record: UsersModel | None
    organizer_record: UsersModel | None
    registration_status: EventRegistrationStatus

    @property
    def organizer_user_id(self) -> int:
        return self.event.organizer_user_id


def sync_dialog_selection(
    dialog_manager: DialogManager,
    *,
    event_id: int | None,
    participant_user_id: int | None,
) -> tuple[int | None, int | None]:
    start_data = (
        dialog_manager.start_data
        if isinstance(dialog_manager.start_data, dict)
        else {}
    )
    resolved_event_id = event_id
    if not isinstance(resolved_event_id, int):
        candidate = start_data.get("event_id")
        if isinstance(candidate, int):
            resolved_event_id = candidate

    resolved_participant_user_id = participant_user_id
    if not isinstance(resolved_participant_user_id, int):
        candidate = start_data.get("participant_user_id")
        if isinstance(candidate, int):
            resolved_participant_user_id = candidate

    if isinstance(resolved_event_id, int):
        dialog_manager.dialog_data[DIALOG_EVENT_ID_KEY] = resolved_event_id
    if isinstance(resolved_participant_user_id, int):
        dialog_manager.dialog_data[DIALOG_PARTICIPANT_USER_ID_KEY] = (
            resolved_participant_user_id
        )

    return resolved_event_id, resolved_participant_user_id


def format_user_label(*, user_id: int, username: str | None) -> str:
    return f"@{username}" if username else f"id:{user_id}"


def build_event_dialog_callback_data(*, event_id: int, participant_user_id: int) -> str:
    return f"{EVENT_DIALOG_OPEN_CALLBACK}:{event_id}:{participant_user_id}"


def build_event_dialog_keyboard(
    *,
    i18n: TranslatorRunner,
    event_id: int,
    participant_user_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.dialog.open.button(),
                    callback_data=build_event_dialog_callback_data(
                        event_id=event_id,
                        participant_user_id=participant_user_id,
                    ),
                )
            ]
        ]
    )


def build_dialog_notification_text(
    *,
    i18n: TranslatorRunner,
    text: str,
    event_name: str,
    sender_label: str,
    sender_is_organizer: bool,
) -> str:
    escaped_text = escape(text)
    if sender_is_organizer:
        return i18n.partner.event.dialog.notification.organizer(
            event_name=event_name,
            sender=sender_label,
            text=f"<blockquote>{escaped_text}</blockquote>",
        )
    return i18n.partner.event.dialog.notification.participant(
        event_name=event_name,
        sender=sender_label,
        text=f"<blockquote>{escaped_text}</blockquote>",
    )


async def has_participant_dialog_access(
    *,
    db: DB,
    participant_user_id: int,
    event_id: int,
) -> bool:
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or is_event_past(event.event_datetime):
        return False

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=participant_user_id,
    )
    return bool(
        registration
        and registration.status in PARTICIPANT_ALLOWED_STATUSES
    )


async def has_organizer_dialog_access(
    *,
    db: DB,
    organizer_user_id: int,
    event_id: int,
    participant_user_id: int,
) -> bool:
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or event.organizer_user_id != organizer_user_id:
        return False

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=participant_user_id,
    )
    return bool(
        registration
        and registration.status in ORGANIZER_ALLOWED_STATUSES
    )


async def get_participant_dialog_context(
    *,
    db: DB,
    participant_user_id: int,
    event_id: int,
) -> EventDialogContext | None:
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or is_event_past(event.event_datetime):
        return None

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=participant_user_id,
    )
    if registration is None or registration.status not in PARTICIPANT_ALLOWED_STATUSES:
        return None

    participant_record = await db.users.get_user_record(user_id=participant_user_id)
    organizer_record = await db.users.get_user_record(user_id=event.organizer_user_id)
    return EventDialogContext(
        event=event,
        participant_user_id=participant_user_id,
        participant_record=participant_record,
        organizer_record=organizer_record,
        registration_status=registration.status,
    )


async def get_organizer_dialog_context(
    *,
    db: DB,
    organizer_user_id: int,
    event_id: int,
    participant_user_id: int,
) -> EventDialogContext | None:
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or event.organizer_user_id != organizer_user_id:
        return None

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=participant_user_id,
    )
    if registration is None or registration.status not in ORGANIZER_ALLOWED_STATUSES:
        return None

    participant_record = await db.users.get_user_record(user_id=participant_user_id)
    organizer_record = await db.users.get_user_record(user_id=organizer_user_id)
    return EventDialogContext(
        event=event,
        participant_user_id=participant_user_id,
        participant_record=participant_record,
        organizer_record=organizer_record,
        registration_status=registration.status,
    )


async def get_dialog_context_for_user(
    *,
    db: DB,
    current_user_id: int,
    event_id: int,
    participant_user_id: int,
) -> tuple[EventDialogContext | None, bool]:
    organizer_context = await get_organizer_dialog_context(
        db=db,
        organizer_user_id=current_user_id,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    if organizer_context is not None:
        return organizer_context, True

    participant_context = await get_participant_dialog_context(
        db=db,
        participant_user_id=current_user_id,
        event_id=event_id,
    )
    if participant_context is None or current_user_id != participant_user_id:
        return None, False
    return participant_context, False
