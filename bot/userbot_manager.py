# -*- coding: utf-8 -*-
"""UserBot manager using Telethon for monitoring groups"""

import asyncio
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    FloodWaitError, InviteHashExpiredError, UserAlreadyParticipantError,
    ChannelInvalidError, ChannelPrivateError, SessionPasswordNeededError
)

logger = logging.getLogger(__name__)

# DB keys used to persist transient login state across restarts
_DB_KEY_LOGIN_PHONE = "_login_phone"
_DB_KEY_LOGIN_HASH  = "_login_phone_code_hash"


class UserBotManager:
    """Manages the UserBot for monitoring Telegram groups"""

    def __init__(self, api_id: int, api_hash: str, session_string: str = None, db=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.db = db
        self.client: Optional[TelegramClient] = None
        self.is_connected = False
        self.is_running = False
        self.message_handler: Optional[Callable] = None
        self._handlers = []
        self._phone: Optional[str] = None
        self._phone_code_hash: Optional[str] = None

    # ── Login state persistence ─────────────────────────────────────
    # Guarantees that (phone, phone_code_hash) survive a process restart
    # that might happen between send_code() and verify_code().

    def _persist_login_state(self) -> None:
        """Save phone + code hash to the DB settings table."""
        if self.db is None:
            return
        try:
            if self._phone:
                self.db.set_setting(_DB_KEY_LOGIN_PHONE, self._phone)
            if self._phone_code_hash:
                self.db.set_setting(_DB_KEY_LOGIN_HASH, self._phone_code_hash)
        except Exception as exc:
            logger.warning(f"Could not persist login state: {exc}")

    def _load_login_state(self) -> None:
        """Restore phone + code hash from DB into memory if not already set."""
        if self.db is None:
            return
        try:
            if not self._phone:
                stored = self.db.get_setting(_DB_KEY_LOGIN_PHONE)
                if stored:
                    self._phone = stored
            if not self._phone_code_hash:
                stored = self.db.get_setting(_DB_KEY_LOGIN_HASH)
                if stored:
                    self._phone_code_hash = stored
        except Exception as exc:
            logger.warning(f"Could not load login state: {exc}")

    def _clear_login_state(self) -> None:
        """Erase transient login state from both memory and DB."""
        self._phone = None
        self._phone_code_hash = None
        if self.db is None:
            return
        try:
            self.db.set_setting(_DB_KEY_LOGIN_PHONE, "")
            self.db.set_setting(_DB_KEY_LOGIN_HASH, "")
        except Exception as exc:
            logger.warning(f"Could not clear login state: {exc}")

    # ── Client lifecycle ────────────────────────────────────────────

    async def create_client(self, phone: str = None, session_string: str = None):
        """Create or restore Telegram client — always disconnects existing client first."""
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None
            self.is_connected = False

        if session_string:
            self.client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
        elif phone:
            # Fresh login — erase any stale state from a previous incomplete flow
            self._clear_login_state()
            self.client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash
            )
            self._phone = phone
        else:
            self.client = TelegramClient(
                StringSession(self.session_string) if self.session_string else StringSession(),
                self.api_id,
                self.api_hash
            )
        return self.client

    # ── Login flow ──────────────────────────────────────────────────

    async def send_code(self, phone: str) -> Dict:
        """Send verification code to phone.

        Persists (phone, phone_code_hash) to the DB so verify_code()
        can recover them even if the process restarts between steps.
        """
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                result = await self.client.send_code_request(phone)
                self._phone = phone
                self._phone_code_hash = result.phone_code_hash
                self._persist_login_state()
                return {
                    "status": "code_sent",
                    "phone_code_hash": result.phone_code_hash
                }
            else:
                return {"status": "already_authorized"}
        except Exception as exc:
            logger.error(f"Send code error: {exc}")
            return {"status": "error", "error": str(exc)}

    async def verify_code(self, code: str) -> Dict:
        """Verify OTP code and complete login — handles 2FA if needed.

        Falls back to DB-persisted phone/hash if memory was lost after restart.
        """
        try:
            self._load_login_state()

            if not self._phone or not self._phone_code_hash:
                return {
                    "status": "error",
                    "error": "Phone or code hash not found. Please start over."
                }

            await self.client.sign_in(
                self._phone, code,
                phone_code_hash=self._phone_code_hash
            )

            me = await self.client.get_me()
            session_string = StringSession.save(self.client.session)
            self.is_connected = True
            phone = self._phone
            self._clear_login_state()

            return {
                "status": "connected",
                "phone": phone,
                "session_string": session_string,
                "user_id": me.id,
                "username": me.username or ""
            }

        except SessionPasswordNeededError:
            # Do NOT clear state — phone is still needed by verify_password
            return {"status": "2fa_required", "error": "Two-step verification is enabled"}

        except Exception as exc:
            logger.error(f"Verify code error: {exc}")
            return {"status": "error", "error": str(exc)}

    async def verify_password(self, password: str) -> Dict:
        """Complete 2FA verification with password.

        Loads phone from DB if memory was lost between steps.
        """
        try:
            self._load_login_state()
            phone = self._phone or ""

            await self.client.sign_in(password=password)

            me = await self.client.get_me()
            session_string = StringSession.save(self.client.session)
            self.is_connected = True
            self._clear_login_state()

            return {
                "status": "connected",
                "phone": phone,
                "session_string": session_string,
                "user_id": me.id,
                "username": me.username or ""
            }

        except Exception as exc:
            logger.error(f"2FA verification error: {exc}")
            return {"status": "error", "error": str(exc)}

    # ── Session management ──────────────────────────────────────────

    async def connect_existing(self, session_string: str) -> Dict:
        """Connect using an existing session string."""
        try:
            self.client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
            await self.client.connect()

            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self.is_connected = True
                return {
                    "status": "connected",
                    "user_id": me.id,
                    "username": me.username or ""
                }
            else:
                return {"status": "not_authorized"}

        except Exception as exc:
            logger.error(f"Connect existing error: {exc}")
            return {"status": "error", "error": str(exc)}

    async def disconnect(self):
        """Disconnect the UserBot and clean up handlers."""
        self.is_running = False
        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except Exception:
                pass
        self._handlers = []
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
        self.is_connected = False

    # ── Monitoring ──────────────────────────────────────────────────

    def set_message_handler(self, handler: Callable):
        """Set callback for new messages."""
        self.message_handler = handler

    async def start_monitoring(self, groups: List[Dict]):
        """Start monitoring a specific list of groups for messages."""
        if not self.client or not self.is_connected:
            logger.error("Client not connected")
            return False

        self.is_running = True

        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except Exception:
                pass
        self._handlers = []

        monitored_ids = [
            g["chat_id"] for g in groups
            if g.get("is_active", 1) and g.get("chat_id", 0) != 0
        ]

        if not monitored_ids:
            logger.warning("No active groups with valid IDs to monitor")
            return True

        @self.client.on(events.NewMessage(chats=monitored_ids))
        async def handle_new_message(event):
            if not self.is_running:
                return
            try:
                chat = await event.get_chat()
                message_text = event.message.text or event.message.message or ""
                if not message_text:
                    return
                sender = await event.get_sender()
                sender_username = (
                    f"@{sender.username}"
                    if sender and hasattr(sender, "username") and sender.username
                    else "مجهول"
                )
                sender_id = sender.id if sender else 0
                chat_username = getattr(chat, "username", None)

                if self.message_handler:
                    await self.message_handler({
                        "message_id": event.message.id,
                        "chat_id": event.chat_id,
                        "chat_title": getattr(chat, "title", "Unknown"),
                        "chat_username": chat_username,
                        "text": message_text,
                        "sender_username": sender_username,
                        "sender_id": sender_id,
                        "date": event.message.date,
                        "type": "new_message"
                    })
            except Exception as exc:
                logger.error(f"Error handling message: {exc}")

        self._handlers.append(handle_new_message)
        logger.info(f"Started monitoring {len(monitored_ids)} groups")
        return True

    async def start_monitoring_all(self) -> int:
        """Monitor ALL groups/channels the account is a member of.

        Steps:
          1. Syncs every dialog from the account into the database (new only).
          2. Registers a global handler (no chat-ID filter) so every
             new message from any group/channel reaches message_handler
             where keyword filtering happens in bot_manager as usual.

        Returns the number of dialogs discovered and synced.
        """
        if not self.client or not self.is_connected:
            logger.error("Client not connected for monitor-all")
            return 0

        self.is_running = True

        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except Exception:
                pass
        self._handlers = []

        discovered = await self.sync_all_dialogs()

        @self.client.on(events.NewMessage(
            func=lambda e: e.is_group or e.is_channel
        ))
        async def handle_all_messages(event):
            if not self.is_running:
                return
            try:
                chat = await event.get_chat()
                message_text = event.message.text or event.message.message or ""
                if not message_text:
                    return
                sender = await event.get_sender()
                sender_username = (
                    f"@{sender.username}"
                    if sender and hasattr(sender, "username") and sender.username
                    else "مجهول"
                )
                sender_id = sender.id if sender else 0
                chat_username = getattr(chat, "username", None)

                if self.message_handler:
                    await self.message_handler({
                        "message_id": event.message.id,
                        "chat_id": event.chat_id,
                        "chat_title": getattr(chat, "title", "Unknown"),
                        "chat_username": chat_username,
                        "text": message_text,
                        "sender_username": sender_username,
                        "sender_id": sender_id,
                        "date": event.message.date,
                        "type": "new_message"
                    })
            except Exception as exc:
                logger.error(f"Error in monitor-all handler: {exc}")

        self._handlers.append(handle_all_messages)
        logger.info(f"Started monitoring ALL dialogs ({discovered} synced to DB)")
        return discovered

    async def sync_all_dialogs(self) -> int:
        """Fetch ALL groups/channels the account is in and upsert them
        into the database (new ones only — existing rows are not touched).

        Returns the total count of group/channel dialogs found.
        """
        if not self.client or not self.is_connected:
            return 0

        count = 0
        try:
            async for dialog in self.client.iter_dialogs():
                if not (dialog.is_group or dialog.is_channel):
                    continue
                entity = dialog.entity
                chat_id = dialog.id
                title = dialog.title or "Unknown"
                username = getattr(entity, "username", None)
                member_count = getattr(entity, "participants_count", 0) or 0
                is_private = not bool(username)

                if self.db:
                    try:
                        existing = self.db.get_group(chat_id)
                        if not existing:
                            self.db.add_group(
                                chat_id=chat_id,
                                title=title,
                                username=username,
                                invite_link=f"https://t.me/{username}" if username else None,
                                member_count=member_count,
                                is_private=is_private
                            )
                    except Exception as exc:
                        logger.warning(f"DB upsert failed for chat {chat_id}: {exc}")
                count += 1
        except Exception as exc:
            logger.error(f"sync_all_dialogs error: {exc}")

        return count

    async def stop_monitoring(self):
        """Stop all monitoring handlers."""
        self.is_running = False
        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except Exception:
                pass
        self._handlers = []
        logger.info("Stopped monitoring")

    # ── Group operations ────────────────────────────────────────────

    async def join_group(self, invite_link: str) -> Dict:
        """Join a group using invite link or username."""
        try:
            if "/+" in invite_link:
                hash_part = invite_link.split("/+")[-1]
                result = await self.client(ImportChatInviteRequest(hash_part))
                chat = result.chats[0] if hasattr(result, "chats") and result.chats else None

            elif "joinchat/" in invite_link:
                hash_part = invite_link.split("joinchat/")[-1]
                result = await self.client(ImportChatInviteRequest(hash_part))
                chat = result.chats[0] if hasattr(result, "chats") and result.chats else None

            elif "t.me/" in invite_link or "telegram.me/" in invite_link:
                username = invite_link.split("/")[-1].replace("@", "")
                entity = await self.client.get_entity(username)
                await self.client(JoinChannelRequest(entity))
                chat = entity

            elif invite_link.startswith("@"):
                entity = await self.client.get_entity(invite_link)
                await self.client(JoinChannelRequest(entity))
                chat = entity

            else:
                return {"success": False, "error": "صيغة الرابط غير معروفة"}

            if chat:
                return {
                    "success": True,
                    "chat_id": chat.id,
                    "title": getattr(chat, "title", "Unknown"),
                    "username": getattr(chat, "username", None),
                    "member_count": getattr(chat, "participants_count", 0)
                }
            return {"success": False, "error": "لم يتم العثور على القروب"}

        except InviteHashExpiredError:
            return {"success": False, "error": "الرابط منتهي الصلاحية"}
        except UserAlreadyParticipantError:
            try:
                if "t.me/" in invite_link or "telegram.me/" in invite_link:
                    username = invite_link.split("/")[-1].replace("@", "")
                    entity = await self.client.get_entity(username)
                elif invite_link.startswith("@"):
                    entity = await self.client.get_entity(invite_link)
                else:
                    return {
                        "success": False,
                        "error": "الحساب موجود بالفعل في القروب ولا يمكن الحصول على المعلومات"
                    }
                return {
                    "success": True,
                    "chat_id": entity.id,
                    "title": getattr(entity, "title", "Unknown"),
                    "username": getattr(entity, "username", None),
                    "member_count": getattr(entity, "participants_count", 0)
                }
            except Exception as exc:
                return {"success": False, "error": f"الحساب موجود بالفعل: {exc}"}
        except FloodWaitError as exc:
            return {"success": False, "error": f"انتظر {exc.seconds} ثانية ثم أعد المحاولة"}
        except ChannelInvalidError:
            return {"success": False, "error": "القروب غير صالح"}
        except ChannelPrivateError:
            return {"success": False, "error": "القروب خاص ولا يمكن الوصول إليه"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def leave_group(self, chat_id: int):
        """Leave a group."""
        try:
            entity = await self.client.get_entity(chat_id)
            await self.client(LeaveChannelRequest(entity))
            return True
        except Exception as exc:
            logger.error(f"Error leaving group: {exc}")
            return False

    async def get_group_info(self, chat_id: int) -> Optional[Dict]:
        """Get group information."""
        try:
            entity = await self.client.get_entity(chat_id)
            return {
                "chat_id": entity.id,
                "title": getattr(entity, "title", "Unknown"),
                "username": getattr(entity, "username", None),
                "member_count": getattr(entity, "participants_count", 0)
            }
        except Exception as exc:
            logger.error(f"Error getting group info: {exc}")
            return None

    async def get_dialogs(self) -> List[Dict]:
        """Get all group/channel dialogs the account is in."""
        try:
            dialogs = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    dialogs.append({
                        "chat_id": dialog.id,
                        "title": dialog.title,
                        "username": (
                            dialog.entity.username
                            if hasattr(dialog.entity, "username")
                            else None
                        ),
                        "is_group": dialog.is_group,
                        "is_channel": dialog.is_channel
                    })
            return dialogs
        except Exception as exc:
            logger.error(f"Error getting dialogs: {exc}")
            return []

    # ── Health ──────────────────────────────────────────────────────

    async def check_health(self) -> Dict:
        """Check userbot health status."""
        try:
            if not self.client or not self.is_connected:
                return {"status": "disconnected", "healthy": False}

            me = await self.client.get_me()
            dialogs = await self.get_dialogs()

            return {
                "status": "connected",
                "healthy": True,
                "user_id": me.id,
                "username": me.username,
                "groups_count": len(dialogs)
            }
        except Exception as exc:
            return {"status": "error", "healthy": False, "error": str(exc)}
