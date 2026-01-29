import re
from dataclasses import replace

from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey

_INVALID_KEY_CHARS = re.compile(r"[^-/_=.a-zA-Z0-9]+")


def _sanitize(value: str) -> str:
    value = _INVALID_KEY_CHARS.sub("_", value).strip(".")
    return value or "_"


class NatsKeyBuilder(DefaultKeyBuilder):
    def build(self, key: StorageKey, part=None) -> str:
        safe_key = replace(
            key,
            destiny=_sanitize(key.destiny),
            business_connection_id=(
                _sanitize(key.business_connection_id)
                if key.business_connection_id
                else None
            ),
        )
        return super().build(safe_key, part=part)
