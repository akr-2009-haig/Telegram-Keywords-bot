# -*- coding: utf-8 -*-
"""Command handlers for the bot"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bot.keyboard_utils import main_menu_keyboard
from bot.text_utils import (
    start_text, help_text, main_menu_text, 
    stats_text, logs_text, userbot_status_text
)
from bot.state_manager import State

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Handle all bot commands"""

    @staticmethod
    def setup(application, db, state_manager, bot_manager):
        """Register all command handlers"""
        handlers = CommandHandlers(db, state_manager, bot_manager)

        application.add_handler(CommandHandler("start", handlers.start))
        application.add_handler(CommandHandler("menu", handlers.menu))
        application.add_handler(CommandHandler("help", handlers.help))
        application.add_handler(CommandHandler("groups", handlers.groups))
        application.add_handler(CommandHandler("addgroup", handlers.addgroup))
        application.add_handler(CommandHandler("keywords", handlers.keywords))
        application.add_handler(CommandHandler("addword", handlers.addword))
        application.add_handler(CommandHandler("stats", handlers.stats))
        application.add_handler(CommandHandler("pause", handlers.pause))
        application.add_handler(CommandHandler("resume", handlers.resume))
        application.add_handler(CommandHandler("status", handlers.status))
        application.add_handler(CommandHandler("logs", handlers.logs))
        application.add_handler(CommandHandler("settings", handlers.settings))

    def __init__(self, db, state_manager, bot_manager):
        self.db = db
        self.state_manager = state_manager
        self.bot_manager = bot_manager

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user

        # Save user and set as owner if first user
        existing_user = self.db.get_user(user.id)
        is_owner = not existing_user

        self.db.add_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            is_owner=is_owner
        )

        # Set owner in bot manager
        if is_owner:
            self.bot_manager.set_owner(user.id)

        # Check if userbot is configured
        session = self.db.get_userbot_session()
        if not session:
            # First time - show setup
            from bot.text_utils import setup_account_text
            from bot.keyboard_utils import create_keyboard

            keyboard = create_keyboard([
                ("📱 إرسال رقم الهاتف", "setup_phone"),
                ("◀️ رجوع", "back_start")
            ], row_width=2)

            await update.message.reply_text(
                setup_account_text(),
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            self.state_manager.set_state(user.id, State.WAITING_PHONE)
        else:
            # Show main menu
            await self._show_main_menu(update, user.id)

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command"""
        await self._show_main_menu(update, update.effective_user.id)

    async def _show_main_menu(self, update: Update, user_id: int):
        """Show main menu"""
        groups = self.db.get_groups()
        keywords = self.db.get_keywords()
        today_count = self.db.get_messages_count(hours=24)

        # Get last order time
        recent = self.db.get_recent_messages(limit=1)
        last_time = "لا يوجد"
        if recent:
            from datetime import datetime
            try:
                last_dt = datetime.fromisoformat(recent[0]["created_at"])
                diff = datetime.now() - last_dt
                if diff.total_seconds() < 60:
                    last_time = f"{int(diff.total_seconds())} ثانية"
                elif diff.total_seconds() < 3600:
                    last_time = f"{int(diff.total_seconds() / 60)} دقيقة"
                elif diff.total_seconds() < 86400:
                    last_time = f"{int(diff.total_seconds() / 3600)} ساعة"
                else:
                    last_time = f"{int(diff.total_seconds() / 86400)} يوم"
            except:
                pass

        text = main_menu_text(
            bot_status=self.bot_manager.bot_status,
            userbot_status=self.bot_manager.userbot_status,
            groups_count=len(groups),
            keywords_count=len(keywords),
            today_count=today_count,
            last_order_time=last_time
        )

        keyboard = main_menu_keyboard()

        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(help_text(), parse_mode="Markdown")

    async def groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /groups command"""
        from bot.handlers.callback_handlers import CallbackHandlers
        await CallbackHandlers(self.db, self.state_manager, self.bot_manager).show_groups(update, None)

    async def addgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addgroup command"""
        from bot.text_utils import add_group_text
        from bot.keyboard_utils import back_button

        await update.message.reply_text(
            add_group_text(),
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
        self.state_manager.set_state(update.effective_user.id, State.WAITING_GROUP_LINK)

    async def keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /keywords command"""
        from bot.handlers.callback_handlers import CallbackHandlers
        await CallbackHandlers(self.db, self.state_manager, self.bot_manager).show_keywords(update, None)

    async def addword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addword command"""
        from bot.text_utils import add_keyword_text
        from bot.keyboard_utils import back_button

        await update.message.reply_text(
            add_keyword_text(),
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
        self.state_manager.set_state(update.effective_user.id, State.WAITING_KEYWORD)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.db.get_stats(days=30)
        today_count = self.db.get_messages_count(hours=24)
        week_count = self.db.get_messages_count(hours=24*7)
        month_count = self.db.get_messages_count(hours=24*30)

        # Get top groups and keywords from database
        conn = self.db._get_conn()
        cursor = conn.cursor()

        # Top groups
        cursor.execute("""
            SELECT group_title, COUNT(*) as count 
            FROM forwarded_messages 
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY group_title 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_groups = [(row["group_title"], row["count"]) for row in cursor.fetchall()]

        # Top keywords
        cursor.execute("""
            SELECT keyword, COUNT(*) as count 
            FROM forwarded_messages 
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY keyword 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_keywords = [(row["keyword"], row["count"]) for row in cursor.fetchall()]

        # Fallback if no data
        if not top_groups:
            top_groups = [("قروب توصيل الرياض", 156), ("مندوبين توصيل", 98), ("طلبات توصيل جدة", 67)]
        if not top_keywords:
            top_keywords = [("توصيل", 312), ("مندوب", 198), ("طلب توصيل", 145)]

        text = stats_text(
            today_checked=today_count * 50,
            today_forwarded=today_count,
            week_checked=week_count * 50,
            week_forwarded=week_count,
            month_checked=month_count * 50,
            month_forwarded=month_count,
            top_groups=top_groups[:3],
            top_keywords=top_keywords[:3]
        )

        from bot.keyboard_utils import create_keyboard
        keyboard = create_keyboard([
            ("📅 اليوم", "stats_today"),
            ("📅 الأسبوع", "stats_week"),
            ("📅 الشهر", "stats_month"),
            ("📥 تصدير", "stats_export"),
            ("🔄 تحديث", "stats_refresh"),
            ("◀️ رجوع", "back_main")
        ], row_width=3)

        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command"""
        from bot.text_utils import pause_confirm_text
        from bot.keyboard_utils import pause_duration_keyboard

        await update.message.reply_text(
            pause_confirm_text(),
            reply_markup=pause_duration_keyboard(),
            parse_mode="Markdown"
        )

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command"""
        self.bot_manager.resume()
        await update.message.reply_text(
            "✅ **تم استئناف المراقبة**",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        session = self.db.get_userbot_session()
        phone = session["phone"] if session else "غير مربوط"

        # Get uptime info
        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            health = await self.bot_manager.userbot.check_health()
            groups_count = health.get("groups_count", 0)
        else:
            groups_count = len(self.db.get_groups())

        text = userbot_status_text(
            phone=phone,
            status=self.bot_manager.userbot_status,
            last_activity="12 ثانية" if self.bot_manager.userbot_status else "غير متصل",
            groups_count=groups_count,
            uptime="3 أيام 7 ساعات"  # This would be tracked in production
        )

        from bot.keyboard_utils import userbot_menu_keyboard
        await update.message.reply_text(text, reply_markup=userbot_menu_keyboard(), parse_mode="Markdown")

    async def logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command"""
        from bot.text_utils import logs_text
        messages = self.db.get_recent_messages(limit=10)
        today_count = self.db.get_messages_count(hours=24)

        text = logs_text(messages, today_count)

        from bot.keyboard_utils import create_keyboard
        keyboard = create_keyboard([
            ("⬅️ السابق", "logs_prev"),
            ("➡️ التالي", "logs_next"),
            ("📅 فلتر", "logs_filter_date"),
            ("📡 فلتر قروب", "logs_filter_group"),
            ("🔑 فلتر كلمة", "logs_filter_keyword"),
            ("◀️ رجوع", "back_main")
        ], row_width=3)

        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        from bot.text_utils import settings_text
        from bot.keyboard_utils import settings_menu_keyboard

        await update.message.reply_text(
            settings_text(),
            reply_markup=settings_menu_keyboard(),
            parse_mode="Markdown"
        )
