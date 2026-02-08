import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import settings


def _parse_api_id(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _build_session(session_value: str) -> StringSession | str:
    value = (session_value or "").strip()
    if not value:
        return "hol_club_telethon"
    try:
        return StringSession(value)
    except Exception:
        return value


async def _run() -> int:
    api_id = _parse_api_id(settings.get("telethon_api_id"))
    api_hash = str(settings.get("telethon_api_hash") or "").strip()
    session_value = str(settings.get("telethon_session") or "").strip()

    if not api_id or not api_hash:
        print(
            "Missing TELETHON_API_ID/TELETHON_API_HASH in .env",
            file=sys.stderr,
        )
        return 1

    session = _build_session(session_value)
    client = TelegramClient(session, api_id, api_hash)
    try:
        await client.start()
        me = await client.get_me()
        username = f"@{me.username}" if getattr(me, "username", None) else "-"
        print(f"Authorized as id={me.id}, username={username}")
        if isinstance(session, StringSession):
            session_string = session.save()
            print("String session is active.")
            print("Keep TELETHON_SESSION as a valid StringSession value.")
            print(session_string)
        else:
            print(f"Session file is active: {session}.session")
        return 0
    finally:
        await client.disconnect()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
