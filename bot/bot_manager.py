# -*- coding: utf-8 -*-
"""Main bot manager - coordinates bot, userbot, and all handlers"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from telegram import Update, Bot
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
from bot.keyboard_utils import main_menu_keyboard
from bot.text_utils import main_menu_text

logger = logging.getLogger(__name__)

class BotManager:
    """Main manager coordinating all bot components"""

    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.db_path)
        self.state_manager = StateManager()
        self.userbot: Optional[UserBotManager] = None
        self.application: Optional[Application] = None
        self.running = False
        self.bot_status = False
        self.userbot_status = False
        self._paused_until = None
        self._owner_id = None
        self._last_health_check = None

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

    async def start(self):
        """Start the bot application"""
        if not self.config.bot_token:
            logger.error("Bot token not configured!")
            return

        # Build application
        self.application = (
            Application.builder()
            .token(self.config.bot_token)
            .build()
        )

        # Setup handlers
        self._setup_handlers()

        # Initialize handlers with references
        CommandHandlers.setup(self.application, self.db, self.state_manager, self)
        CallbackHandlers.setup(self.application, self.db, self.state_manager, self)
        MessageHandlers.setup(self.application, self.db, self.state_manager, self)

        # Start bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

        self.running = True
        self.bot_status = True
        logger.info("Bot started successfully!")

        # Connect userbot if session exists
        await self._connect_userbot()

        # Start health check loop
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
                    # Start monitoring
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
                await asyncio.sleep(60)  # Check every minute

                if self.userbot and self.userbot.is_connected:
                    health = await self.userbot.check_health()
                    self.userbot_status = health.get("healthy", False)

                    if not health.get("healthy") and self._owner_id:
                        # Send alert to owner
                        try:
                            await self.application.bot.send_message(
                                chat_id=self._owner_id,
                                text=f"🔴 **تنبيه: الحساب المراقب انقطع!**\n\n"
                                     f"السبب: {health.get('error', 'Unknown')}\n\n"
                                     f"استخدم /status لمعرفة التفاصيل",
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send alert: {e}")

            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _handle_monitored_message(self, message_data: Dict[str, Any]):
        """Handle message from monitored groups"""
        # Check if paused
        if self._paused_until and datetime.now() < self._paused_until:
            return

        # Check for special events
        if message_data.get("type") == "removed_from_group":
            await self._send_alert_to_owner(
                f"⚠️ تم إزالة الحساب من قروب: {message_data.get('chat_title', 'Unknown')}"
            )
            return

        text = message_data.get("text", "")
        if not text:
            return

        # Check blacklist first
        blacklist = self.db.get_blacklist()
        for word in blacklist:
            if word.lower() in text.lower():
                return

        # Check keywords
        keywords = self.db.get_keywords()
        matched_keyword = None
        for keyword in keywords:
            if keyword.lower() in text.lower():
                matched_keyword = keyword
                break

        if not matched_keyword:
            return

        # Get destination group
        dest_group_id = self.db.get_setting("destination_group_id")
        if not dest_group_id:
            return

        try:
            dest_group_id = int(dest_group_id)
        except:
            return

        # Format and send message
        order_num = self.db.get_messages_count(hours=24) + 1

        msg_date = message_data.get("date", datetime.now())
        if isinstance(msg_date, datetime):
            time_str = msg_date.strftime("%I:%M %p — %d %B %Y")
        else:
            time_str = str(msg_date)

        # Get format type
        format_type = self.db.get_setting("message_format", "full")

        if format_type == "short":
            formatted_text = f"""📥 طلب #{order_num} | {message_data.get('chat_title', 'Unknown')}
👤 {message_data.get('sender_username', 'Unknown')}
🔑 "{matched_keyword}"

💬 {text[:200]}"""
        elif format_type == "raw":
            formatted_text = text
        else:
            # Full format
            formatted_text = f"""📥 **طلب جديد** #طلب_{order_num}

📡 **المصدر:** {message_data.get('chat_title', 'Unknown')}
👤 **المرسل:** {message_data.get('sender_username', 'Unknown')}
🔑 **الكلمة المطابقة:** "{matched_keyword}"
🕐 **الوقت:** {time_str}

💬 **نص الطلب:**
"{text}"""

        try:
            if self.application and self.application.bot:
                await self.application.bot.send_message(
                    chat_id=dest_group_id,
                    text=formatted_text,
                    parse_mode="Markdown"
                )

                # Save to database
                self.db.add_forwarded_message(
                    original_message_id=message_data.get("message_id", 0),
                    original_chat_id=message_data.get("chat_id", 0),
                    forwarded_message_id=0,
                    forwarded_chat_id=dest_group_id,
                    keyword=matched_keyword,
                    sender_username=message_data.get("sender_username", ""),
                    sender_id=message_data.get("sender_id", 0),
                    message_text=text,
                    group_title=message_data.get("chat_title", "")
                )

                # Update stats
                self.db.increment_stat(messages_checked=1, messages_forwarded=1)

                logger.info(f"Forwarded message with keyword '{matched_keyword}' from {message_data.get('chat_title')}")
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")

    async def _send_alert_to_owner(self, text: str):
        """Send alert to bot owner"""
        if not self._owner_id:
            # Try to find owner from database
            # This is a simplified approach - in production track owner explicitly
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
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

    def set_owner(self, user_id: int):
        """Set bot owner"""
        self._owner_id = user_id

    def _setup_handlers(self):
        """Setup basic handlers"""
        pass

    async def shutdown(self):
        """Shutdown everything gracefully"""
        self.running = False
        self.bot_status = False

        if self.userbot:
            await self.userbot.stop_monitoring()
            await self.userbot.disconnect()

        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

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
        if self._paused_until and datetime.now() < self._paused_until:
            return True
        return False

    async def reconnect_userbot(self):
        """Reconnect userbot"""
        if self.userbot:
            await self.userbot.disconnect()
            await self._connect_userbot()
            return self.userbot_status
        return False
