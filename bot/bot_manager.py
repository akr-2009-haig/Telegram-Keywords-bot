# -*- coding: utf-8 -*-
"""Main bot manager - coordinates bot, userbot, and all handlers"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from bot.config import Config
from bot.database import Database
from bot.state_manager import StateManager, State
from bot.userbot_manager import UserBotManager
from bot.handlers.command_handlers import CommandHandlers
from bot.handlers.callback_handlers import CallbackHandlers
from bot.handlers.message_handlers import MessageHandlers
from bot.keyboard_utils import main_menu_keyboard, forwarded_message_keyboard
from bot.text_utils import main_menu_text

logger = logging.getLogger(__name__)


def escape_md(text: str) -> str:
    """Escape special Markdown characters in text"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


class BotManager:
    """Main manager coordinating all bot components"""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.db_path)
        self.state_manager = StateManager()
        self.userbot: Optional[UserBotManager] = None
        self.application: Optional[Application] = None
        self.running = False
        self.bot_status = True
        self.userbot_status = False
        self._paused_until = None
        self._owner_id = None
        self._start_time = datetime.now()

        # Initialize UserBot
        if config.api_id and config.api_hash:
            session = self.db.get_userbot_session()
            session_string = session["session_string"] if session else None
            self.userbot = UserBotManager(
                api_id=config.api_id,
                api_hash=config.api_hash,
                session_string=session_string,
                db=self.db
            )
            if session:
                self.userbot_status = True

    def get_uptime(self) -> str:
        """Return formatted uptime string"""
        diff = datetime.now() - self._start_time
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        if days > 0:
            return f"{days} يوم {hours} ساعة"
        elif hours > 0:
            return f"{hours} ساعة {minutes} دقيقة"
        else:
            return f"{minutes} دقيقة"

    async def start(self):
        """Start the bot application"""
        if not self.config.bot_token:
            logger.error("Bot token not configured!")
            return

        self.application = (
            Application.builder()
            .token(self.config.bot_token)
            .build()
        )

        CommandHandlers.setup(self.application, self.db, self.state_manager, self)
        CallbackHandlers.setup(self.application, self.db, self.state_manager, self)
        MessageHandlers.setup(self.application, self.db, self.state_manager, self)

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

        self.running = True
        self.bot_status = True
        self._start_time = datetime.now()
        logger.info("Bot started successfully!")

        await self._connect_userbot()
        asyncio.create_task(self._health_check_loop())

    async def _connect_userbot(self):
        """Connect existing userbot session"""
        session = self.db.get_userbot_session()
        if session and self.userbot:
            try:
                result = await self.userbot.connect_existing(session["session_string"])
                if result["status"] == "connected":
                    self.userbot_status = True
                    self.userbot.set_message_handler(self._handle_monitored_message)
                    groups = self.db.get_groups(active_only=True)
                    await self.userbot.start_monitoring(groups)
                    logger.info("UserBot connected and monitoring started")
                else:
                    logger.warning(f"UserBot connection failed: {result}")
                    self.userbot_status = False
            except Exception as e:
                logger.error(f"UserBot connection error: {e}")
                self.userbot_status = False

    async def _health_check_loop(self):
        """Periodic health check for userbot"""
        while self.running:
            try:
                await asyncio.sleep(60)

                if self.userbot and self.userbot.is_connected:
                    health = await self.userbot.check_health()
                    self.userbot_status = health.get("healthy", False)

                    if not health.get("healthy"):
                        session = self.db.get_userbot_session()
                        phone = session["phone"] if session else "غير معروف"
                        await self._send_alert_to_owner(
                            f"🔴 **تنبيه: الحساب المراقب انقطع\\!**\n\n"
                            f"توقف الحساب `{phone}` عن الاستجابة\n"
                            f"السبب: {health.get('error', 'Unknown')}\n\n"
                            f"استخدم /status لمعرفة التفاصيل",
                            keyboard=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔄 إعادة الاتصال", callback_data="restart_userbot"),
                                InlineKeyboardButton("🏠 لوحة التحكم", callback_data="back_main")
                            ]])
                        )

            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _handle_monitored_message(self, message_data: Dict[str, Any]):
        """Handle message from monitored groups"""
        if self.is_paused():
            return

        if message_data.get("type") == "removed_from_group":
            chat_title = message_data.get("chat_title", "Unknown")
            await self._send_alert_to_owner(
                f"⚠️ **تنبيه: تم إزالة الحساب من قروب\\!**\n\n"
                f"تمت إزالة الحساب المراقب من:\n📌 {escape_md(chat_title)}\n\n"
                f"لن يتم مراقبة هذا القروب بعد الآن",
                keyboard=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 لوحة التحكم", callback_data="back_main")
                ]])
            )
            return

        text = message_data.get("text", "")
        if not text:
            return

        # Check blacklist
        blacklist = self.db.get_blacklist()
        for word in blacklist:
            if word.lower() in text.lower():
                self.db.increment_stat(messages_checked=1)
                return

        # Check keywords
        keywords = self.db.get_keywords()
        matched_keyword = None
        for keyword in keywords:
            if keyword.lower() in text.lower():
                matched_keyword = keyword
                break

        if not matched_keyword:
            self.db.increment_stat(messages_checked=1)
            return

        # Check duplicate prevention
        dup_enabled = self.db.get_setting("dup_sender", "1") == "1"
        dup_minutes = int(self.db.get_setting("dup_duration", "30"))
        if dup_enabled and self.db.is_duplicate(
            message_data.get("sender_id", 0), text, minutes=dup_minutes
        ):
            logger.info("Duplicate message suppressed")
            return

        # Get destination group
        dest_group_id = self.db.get_setting("destination_group_id")
        if not dest_group_id:
            logger.warning("No destination group set — cannot forward")
            return

        try:
            dest_group_id = int(dest_group_id)
        except (ValueError, TypeError):
            logger.error("Invalid destination group ID")
            return

        # Format message
        order_num = self.db.get_total_messages_count() + 1
        msg_date = message_data.get("date", datetime.now())
        if isinstance(msg_date, datetime):
            time_str = msg_date.strftime("%I:%M %p — %d/%m/%Y")
        else:
            time_str = str(msg_date)

        format_type = self.db.get_setting("message_format", "full")
        sender = message_data.get("sender_username", "مجهول")
        group_title = message_data.get("chat_title", "Unknown")

        if format_type == "short":
            formatted_text = (
                f"📥 طلب #{order_num} | {group_title}\n"
                f"👤 {sender}\n"
                f"🔑 \"{matched_keyword}\"\n\n"
                f"💬 {text[:300]}"
            )
            parse_mode = None
        elif format_type == "raw":
            formatted_text = text
            parse_mode = None
        else:
            safe_group = escape_md(group_title)
            safe_sender = escape_md(sender)
            safe_keyword = escape_md(matched_keyword)
            safe_time = escape_md(time_str)
            safe_text = escape_md(text[:500])

            formatted_text = (
                f"📥 **طلب جديد** \\#طلب\\_{order_num}\n\n"
                f"📡 **المصدر:** {safe_group}\n"
                f"👤 **المرسل:** {safe_sender}\n"
                f"🔑 **الكلمة المطابقة:** \"{safe_keyword}\"\n"
                f"🕐 **الوقت:** {safe_time}\n\n"
                f"💬 **نص الطلب:**\n\"{safe_text}\""
            )
            parse_mode = "MarkdownV2"

        try:
            if self.application and self.application.bot:
                # Save record first to get ID for action buttons
                record_id = self.db.add_forwarded_message(
                    original_message_id=message_data.get("message_id", 0),
                    original_chat_id=message_data.get("chat_id", 0),
                    forwarded_message_id=0,
                    forwarded_chat_id=dest_group_id,
                    keyword=matched_keyword,
                    sender_username=sender,
                    sender_id=message_data.get("sender_id", 0),
                    message_text=text,
                    group_title=group_title
                )

                # Build action buttons
                reply_markup = forwarded_message_keyboard(
                    record_id=record_id,
                    sender_id=message_data.get("sender_id", 0),
                    sender_username=sender,
                    chat_username=message_data.get("chat_username")
                )

                sent = await self.application.bot.send_message(
                    chat_id=dest_group_id,
                    text=formatted_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )

                self.db.update_forwarded_message_status(record_id, "new")
                self.db.increment_stat(messages_checked=1, messages_forwarded=1)

                logger.info(f"Forwarded message with keyword '{matched_keyword}' from {group_title}")

                # Notify owner if notification enabled
                notif_all = self.db.get_setting("notif_all", "1") == "1"
                if notif_all and self._owner_id:
                    try:
                        await self.application.bot.send_message(
                            chat_id=self._owner_id,
                            text=f"🔔 طلب جديد من *{escape_md(group_title)}*",
                            parse_mode="MarkdownV2"
                        )
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Error forwarding message: {e}")

    async def _send_alert_to_owner(self, text: str, keyboard=None):
        """Send alert to bot owner"""
        if not self._owner_id:
            try:
                conn = self.db._get_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE is_owner = 1 LIMIT 1")
                row = cursor.fetchone()
                if row:
                    self._owner_id = row["id"]
            except Exception as e:
                logger.error(f"Failed to find owner: {e}")
                return

        if self._owner_id and self.application and self.application.bot:
            try:
                await self.application.bot.send_message(
                    chat_id=self._owner_id,
                    text=text,
                    parse_mode="MarkdownV2",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

    def set_owner(self, user_id: int):
        """Set bot owner"""
        self._owner_id = user_id

    async def shutdown(self):
        """Shutdown everything gracefully"""
        self.running = False
        self.bot_status = False

        if self.userbot:
            await self.userbot.stop_monitoring()
            await self.userbot.disconnect()

        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception:
                pass

        logger.info("Bot shutdown complete")

    def pause(self, minutes: int = 0):
        """Pause monitoring"""
        if minutes > 0:
            self._paused_until = datetime.now() + timedelta(minutes=minutes)
        else:
            self._paused_until = datetime.max
        self.bot_status = False
        logger.info(f"Bot paused for {minutes} minutes")

    def resume(self):
        """Resume monitoring"""
        self._paused_until = None
        self.bot_status = True
        logger.info("Bot resumed")

    def is_paused(self) -> bool:
        """Check if bot is paused"""
        if self._paused_until is None:
            return False
        if self._paused_until == datetime.max:
            return True
        return datetime.now() < self._paused_until

    async def reconnect_userbot(self):
        """Reconnect userbot"""
        if self.userbot:
            await self.userbot.disconnect()
            await self._connect_userbot()
            return self.userbot_status
        return False
