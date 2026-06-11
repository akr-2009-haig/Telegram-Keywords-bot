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
        self._phone = None
        self._phone_code_hash = None

    async def create_client(self, phone: str = None, session_string: str = None):
        """Create or restore Telegram client"""
        if session_string:
            self.client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
        elif phone:
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

    async def send_code(self, phone: str) -> Dict:
        """Send verification code to phone"""
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                result = await self.client.send_code_request(phone)
                self._phone = phone
                self._phone_code_hash = result.phone_code_hash
                return {
                    "status": "code_sent",
                    "phone_code_hash": result.phone_code_hash
                }
            else:
                return {"status": "already_authorized"}
        except Exception as e:
            logger.error(f"Send code error: {e}")
            return {"status": "error", "error": str(e)}

    async def verify_code(self, code: str) -> Dict:
        """Verify code and complete login — handles 2FA if needed"""
        try:
            if not self._phone or not self._phone_code_hash:
                return {"status": "error", "error": "Phone not set. Please start over."}

            await self.client.sign_in(self._phone, code, phone_code_hash=self._phone_code_hash)

            me = await self.client.get_me()
            session_string = StringSession.save(self.client.session)
            self.is_connected = True

            return {
                "status": "connected",
                "phone": self._phone,
                "session_string": session_string,
                "user_id": me.id,
                "username": me.username or ""
            }

        except SessionPasswordNeededError:
            return {"status": "2fa_required", "error": "Two-step verification is enabled"}

        except Exception as e:
            logger.error(f"Verify code error: {e}")
            return {"status": "error", "error": str(e)}

    async def verify_password(self, password: str) -> Dict:
        """Complete 2FA verification with password"""
        try:
            await self.client.sign_in(password=password)

            me = await self.client.get_me()
            session_string = StringSession.save(self.client.session)
            self.is_connected = True

            return {
                "status": "connected",
                "phone": self._phone,
                "session_string": session_string,
                "user_id": me.id,
                "username": me.username or ""
            }

        except Exception as e:
            logger.error(f"2FA verification error: {e}")
            return {"status": "error", "error": str(e)}

    async def connect_existing(self, session_string: str) -> Dict:
        """Connect using existing session string"""
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

        except Exception as e:
            logger.error(f"Connect existing error: {e}")
            return {"status": "error", "error": str(e)}

    async def disconnect(self):
        """Disconnect the UserBot"""
        self.is_running = False
        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except:
                pass
        self._handlers = []
        if self.client:
            try:
                await self.client.disconnect()
            except:
                pass
        self.is_connected = False

    def set_message_handler(self, handler: Callable):
        """Set callback for new messages"""
        self.message_handler = handler

    async def start_monitoring(self, groups: List[Dict]):
        """Start monitoring groups for messages"""
        if not self.client or not self.is_connected:
            logger.error("Client not connected")
            return False

        self.is_running = True

        # Remove old handlers
        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except:
                pass
        self._handlers = []

        # Get monitored chat IDs
        monitored_ids = [g["chat_id"] for g in groups if g.get("is_active", 1) and g.get("chat_id", 0) != 0]

        if not monitored_ids:
            logger.warning("No active groups with valid IDs to monitor")
            return True

        @self.client.on(events.NewMessage(chats=monitored_ids))
        async def handle_new_message(event):
            if not self.is_running:
                return

            try:
                chat = await event.get_chat()
                chat_id = event.chat_id

                message_text = event.message.text or event.message.message or ""
                if not message_text:
                    return

                sender = await event.get_sender()
                sender_username = f"@{sender.username}" if sender and hasattr(sender, "username") and sender.username else "مجهول"
                sender_id = sender.id if sender else 0
                chat_username = getattr(chat, "username", None)

                if self.message_handler:
                    await self.message_handler({
                        "message_id": event.message.id,
                        "chat_id": chat_id,
                        "chat_title": getattr(chat, "title", "Unknown"),
                        "chat_username": chat_username,
                        "text": message_text,
                        "sender_username": sender_username,
                        "sender_id": sender_id,
                        "date": event.message.date,
                        "type": "new_message"
                    })

            except Exception as e:
                logger.error(f"Error handling message: {e}")

        self._handlers.append(handle_new_message)
        logger.info(f"Started monitoring {len(monitored_ids)} groups")
        return True

    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        for handler in self._handlers:
            try:
                self.client.remove_event_handler(handler)
            except:
                pass
        self._handlers = []
        logger.info("Stopped monitoring")

    async def join_group(self, invite_link: str) -> Dict:
        """Join a group using invite link or username"""
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
            else:
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
                    return {"success": False, "error": "الحساب موجود بالفعل في القروب ولا يمكن الحصول على المعلومات"}

                return {
                    "success": True,
                    "chat_id": entity.id,
                    "title": getattr(entity, "title", "Unknown"),
                    "username": getattr(entity, "username", None),
                    "member_count": getattr(entity, "participants_count", 0)
                }
            except Exception as e:
                return {"success": False, "error": f"الحساب موجود بالفعل: {str(e)}"}
        except FloodWaitError as e:
            return {"success": False, "error": f"انتظر {e.seconds} ثانية ثم أعد المحاولة"}
        except ChannelInvalidError:
            return {"success": False, "error": "القروب غير صالح"}
        except ChannelPrivateError:
            return {"success": False, "error": "القروب خاص ولا يمكن الوصول إليه"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def leave_group(self, chat_id: int):
        """Leave a group"""
        try:
            entity = await self.client.get_entity(chat_id)
            await self.client(LeaveChannelRequest(entity))
            return True
        except Exception as e:
            logger.error(f"Error leaving group: {e}")
            return False

    async def get_group_info(self, chat_id: int) -> Optional[Dict]:
        """Get group information"""
        try:
            entity = await self.client.get_entity(chat_id)
            return {
                "chat_id": entity.id,
                "title": getattr(entity, "title", "Unknown"),
                "username": getattr(entity, "username", None),
                "member_count": getattr(entity, "participants_count", 0)
            }
        except Exception as e:
            logger.error(f"Error getting group info: {e}")
            return None

    async def get_dialogs(self) -> List[Dict]:
        """Get all dialogs (chats)"""
        try:
            dialogs = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    dialogs.append({
                        "chat_id": dialog.id,
                        "title": dialog.title,
                        "username": dialog.entity.username if hasattr(dialog.entity, "username") else None,
                        "is_group": dialog.is_group,
                        "is_channel": dialog.is_channel
                    })
            return dialogs
        except Exception as e:
            logger.error(f"Error getting dialogs: {e}")
            return []

    async def check_health(self) -> Dict:
        """Check userbot health status"""
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
        except Exception as e:
            return {"status": "error", "healthy": False, "error": str(e)}
