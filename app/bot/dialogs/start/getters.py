from aiogram.types import User
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB

async def get_hello(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str]:
    username = event_from_user.full_name or event_from_user.username or i18n.stranger()
    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_partner = bool(
        user_record and user_record.role in {UserRole.PARTNER, UserRole.ADMIN}
    )
    is_admin = bool(user_record and user_record.role == UserRole.ADMIN)
    return {
        "hello": i18n.start.hello(username=username),
        "create_event_button": i18n.partner.event.create.button(),
        "can_create_event": is_partner,
        "partner_requests_button": i18n.partner.request.list.button(),
        "can_manage_partner_requests": is_admin,
    }
