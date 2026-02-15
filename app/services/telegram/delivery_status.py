from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
)

from app.infrastructure.database.database.db import DB

_BLOCKED_MARKERS = (
    "bot was blocked by the user",
    "forbidden: bot was blocked by the user",
)

_UNREACHABLE_MARKERS = (
    "chat not found",
    "user is deactivated",
    "forbidden: user is deactivated",
    "user not found",
    "bot can't initiate conversation with a user",
)


async def apply_delivery_error_status(
    *,
    db: DB,
    user_id: int,
    error: Exception,
) -> bool:
    if isinstance(error, TelegramForbiddenError):
        error_text = str(error).lower()
        if any(marker in error_text for marker in _BLOCKED_MARKERS):
            await db.users.mark_unreachable(user_id=user_id, is_blocked=True)
        else:
            await db.users.mark_unreachable(user_id=user_id, is_blocked=False)
        return True

    if isinstance(error, TelegramNotFound):
        await db.users.mark_unreachable(user_id=user_id, is_blocked=False)
        return True

    if isinstance(error, TelegramBadRequest):
        error_text = str(error).lower()
        if any(marker in error_text for marker in _BLOCKED_MARKERS):
            await db.users.mark_unreachable(user_id=user_id, is_blocked=True)
            return True
        if any(marker in error_text for marker in _UNREACHABLE_MARKERS):
            await db.users.mark_unreachable(user_id=user_id, is_blocked=False)
            return True

    return False
