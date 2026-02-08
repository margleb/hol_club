import logging
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.errors.rpcerrorlist import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    DeleteChannelRequest,
    EditAdminRequest,
    InviteToChannelRequest,
)
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatAdminRights

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreatedEventChat:
    chat_id: int
    invite_link: str


def _to_bot_chat_id(channel_id: int) -> int:
    return int(f"-100{channel_id}")


def _normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    value = username.strip()
    if not value:
        return None
    if not value.startswith("@"):
        return f"@{value}"
    return value


def _build_session(session_value: str) -> StringSession | str:
    value = (session_value or "").strip()
    if not value:
        return "hol_club_telethon"
    try:
        return StringSession(value)
    except Exception:
        return value


class EventPrivateChatService:
    def __init__(
        self,
        *,
        api_id: int,
        api_hash: str,
        session: str,
    ) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._session = session
        self._client: TelegramClient | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._api_id and self._api_hash)

    async def connect(self) -> bool:
        if not self.enabled:
            logger.warning(
                "Telethon private chat service is disabled: missing api_id/api_hash",
            )
            return False
        if self._client is not None:
            return True

        client = TelegramClient(
            _build_session(self._session),
            self._api_id,
            self._api_hash,
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            logger.error(
                "Telethon session is not authorized. "
                "Provide authorized TELETHON_SESSION.",
            )
            return False
        self._client = client
        logger.info("Telethon private chat service connected")
        return True

    async def disconnect(self) -> None:
        if self._client is None:
            return
        await self._client.disconnect()
        self._client = None
        logger.info("Telethon private chat service disconnected")

    async def create_event_chat(
        self,
        *,
        event_id: int,
        event_name: str,
        partner_user_id: int,
        partner_username: str | None,
    ) -> CreatedEventChat | None:
        client = self._client
        if client is None:
            logger.warning("Telethon private chat service is not connected")
            return None

        created_channel = None
        try:
            title = (event_name or "").strip() or f"Event #{event_id}"
            if len(title) > 120:
                title = title[:117] + "..."

            result = await client(
                CreateChannelRequest(
                    title=title,
                    about=f"Чат мероприятия «{title}»",
                    megagroup=True,
                )
            )
            if not result.chats:
                logger.warning("CreateChannelRequest returned empty chats for event %s", event_id)
                return None
            created_channel = result.chats[0]
            channel_entity = await client.get_input_entity(created_channel)

            partner_entity = await self._resolve_partner_entity(
                client=client,
                partner_user_id=partner_user_id,
                partner_username=partner_username,
            )
            if partner_entity is None:
                logger.warning(
                    "Failed to resolve partner entity for event %s and partner %s",
                    event_id,
                    partner_user_id,
                )
                await self._safe_delete_channel(client=client, channel=channel_entity)
                return None

            await client(
                InviteToChannelRequest(
                    channel=channel_entity,
                    users=[partner_entity],
                )
            )
            await client(
                EditAdminRequest(
                    channel=channel_entity,
                    user_id=partner_entity,
                    admin_rights=ChatAdminRights(
                        change_info=True,
                        delete_messages=True,
                        ban_users=True,
                        invite_users=True,
                        pin_messages=True,
                        manage_call=True,
                        manage_topics=True,
                        post_stories=True,
                        edit_stories=True,
                        delete_stories=True,
                    ),
                    rank="Организатор",
                )
            )
            invite = await client(ExportChatInviteRequest(peer=channel_entity))
            invite_link = getattr(invite, "link", None)
            chat_id = getattr(created_channel, "id", None)
            if not invite_link or not isinstance(chat_id, int):
                logger.warning(
                    "Invalid private chat data for event %s: chat_id=%s, invite=%s",
                    event_id,
                    chat_id,
                    bool(invite_link),
                )
                await self._safe_delete_channel(client=client, channel=channel_entity)
                return None
            return CreatedEventChat(
                chat_id=_to_bot_chat_id(chat_id),
                invite_link=invite_link,
            )
        except FloodWaitError as exc:
            logger.warning(
                "Telethon flood wait while creating event chat %s: %s sec",
                event_id,
                exc.seconds,
            )
            if created_channel is not None:
                try:
                    channel_entity = await client.get_input_entity(created_channel)
                    await self._safe_delete_channel(client=client, channel=channel_entity)
                except Exception:
                    pass
            return None
        except RPCError as exc:
            logger.warning(
                "Telethon RPC error while creating event chat %s: %s",
                event_id,
                exc,
            )
            if created_channel is not None:
                try:
                    channel_entity = await client.get_input_entity(created_channel)
                    await self._safe_delete_channel(client=client, channel=channel_entity)
                except Exception:
                    pass
            return None
        except Exception as exc:
            logger.warning(
                "Failed to create private event chat %s: %s",
                event_id,
                exc,
            )
            if created_channel is not None:
                try:
                    channel_entity = await client.get_input_entity(created_channel)
                    await self._safe_delete_channel(client=client, channel=channel_entity)
                except Exception:
                    pass
            return None

    async def delete_event_chat(self, *, chat_id: int) -> None:
        client = self._client
        if client is None:
            return
        peer_id: int | str = chat_id
        chat_id_str = str(chat_id)
        if chat_id_str.startswith("-100"):
            peer_id = int(chat_id_str[4:])
        try:
            channel = await client.get_input_entity(peer_id)
            await client(DeleteChannelRequest(channel=channel))
        except Exception as exc:
            logger.warning("Failed to delete event chat %s: %s", chat_id, exc)

    async def _resolve_partner_entity(
        self,
        *,
        client: TelegramClient,
        partner_user_id: int,
        partner_username: str | None,
    ):
        username = _normalize_username(partner_username)
        if username:
            try:
                return await client.get_input_entity(username)
            except Exception:
                logger.warning("Failed to resolve partner by username %s", username)
        try:
            return await client.get_input_entity(partner_user_id)
        except Exception:
            logger.warning("Failed to resolve partner by user_id %s", partner_user_id)
            return None

    async def _safe_delete_channel(
        self,
        *,
        client: TelegramClient,
        channel,
    ) -> None:
        try:
            await client(DeleteChannelRequest(channel=channel))
        except Exception as exc:
            logger.warning("Failed to delete temporary channel: %s", exc)
