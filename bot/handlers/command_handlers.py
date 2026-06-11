# -*- coding: utf-8 -*-
"""Command handlers for the bot"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

from bot.keyboard_utils import main_menu_keyboard, create_keyboard, back_button
from bot.text_utils import (
    main_menu_text, help_text, status_text, groups_menu_text,
    keywords_menu_text, start_text
)
from bot.state_manager import State

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handle all bot commands"""

    @staticmethod
    def setup(application: Application, db, state_manager, bot_manager):
        """Register all command handlers"""
        handlers = CommandHandlers(db, state_manager, bot_manager)
        cmds = [
            ("start", handlers.start),
            ("menu", handlers.menu),
            ("help", handlers.help),
            ("status", handlers.status),
            ("groups", handlers.groups),
            ("keywords", handlers.keywords),
            ("stats", handlers.stats),
            ("pause", handlers.pause),
            ("resume", handlers.resume),
        ]
        for cmd, handler in cmds:
            application.add_handler(CommandHandler(cmd, handler))

    def __init__(self, db, state_manager, bot_manager):
        self.db = db
        self.state_manager = state_manager
        self.bot_manager = bot_manager

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.db.add_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            is_owner=not bool(self.db.get_admins())
        )
        self.bot_manager.set_owner(user.id)
        self.state_manager.clear_state(user.id)

        session = self.db.get_userbot_session()
        if session:
            await update.message.reply_text(
                main_menu_text(
                    bot_running=self.bot_manager.bot_status,
                    userbot_connected=self.bot_manager.userbot_status
                ),
                reply_markup=main_menu_keyboard(self.bot_manager.bot_status),
                parse_mode="Markdown"
            )
        else:
            keyboard = create_keyboard([
                ("🚀 بدء الإعداد", "setup_phone"),
                ("❓ المساعدة", "help")
            ], row_width=2)
            await update.message.reply_text(
                start_text(),
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command — shows main menu"""
        user = update.effective_user
        self.state_manager.clear_state(user.id)
        await update.message.reply_text(
            main_menu_text(
                bot_running=self.bot_manager.bot_status,
                userbot_connected=self.bot_manager.userbot_status
            ),
            reply_markup=main_menu_keyboard(self.bot_manager.bot_status),
            parse_mode="Markdown"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        keyboard = create_keyboard([
            ("🏠 الرئيسية", "back_main"),
            ("📡 القروبات", "menu_groups"),
            ("🔑 الكلمات", "menu_keywords"),
        ], row_width=2)
        await update.message.reply_text(
            help_text(),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        groups_count = len(self.db.get_groups(active_only=True))
        keywords_count = len(self.db.get_keywords())
        today_count = self.db.get_messages_count(hours=24)
        total_count = self.db.get_total_messages_count()
        uptime = self.bot_manager.get_uptime()

        text = status_text(
            bot_running=self.bot_manager.bot_status,
            userbot_connected=self.bot_manager.userbot_status,
            groups_count=groups_count,
            keywords_count=keywords_count,
            today_orders=today_count,
            total_orders=total_count,
            uptime=uptime
        )
        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard(self.bot_manager.bot_status),
            parse_mode="Markdown"
        )

    async def groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /groups command"""
        groups = self.db.get_groups(active_only=False)
        text = groups_menu_text(groups)
        keyboard = create_keyboard([
            ("➕ إضافة قروب", "add_group"),
            ("🗑 حذف قروب", "delete_group"),
            ("🏠 الرئيسية", "back_main")
        ], row_width=2)
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /keywords command"""
        words = self.db.get_keywords()
        text = keywords_menu_text(words)
        keyboard = create_keyboard([
            ("➕ إضافة كلمة", "add_keyword"),
            ("🗑 حذف كلمة", "delete_keyword"),
            ("🏠 الرئيسية", "back_main")
        ], row_width=2)
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.db.get_stats(days=30)
        today_count = self.db.get_messages_count(hours=24)
        groups_count = len(self.db.get_groups(active_only=True))
        keywords_count = len(self.db.get_keywords())

        text = (
            f"📊 **الإحصائيات**\n\n"
            f"📅 آخر 30 يوم:\n"
            f"  • رسائل فُحصت: **{stats['total_checked']:,}**\n"
            f"  • طلبات حُوّلت: **{stats['total_forwarded']:,}**\n\n"
            f"🕐 اليوم:\n"
            f"  • طلبات: **{today_count}**\n\n"
            f"⚙️ الإعدادات الحالية:\n"
            f"  • قروبات نشطة: **{groups_count}**\n"
            f"  • كلمات مفتاحية: **{keywords_count}**\n"
        )
        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard(self.bot_manager.bot_status),
            parse_mode="Markdown"
        )

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command"""
        self.bot_manager.pause(0)
        await update.message.reply_text(
            "⏸ **تم إيقاف المراقبة مؤقتاً**\n\nاستخدم /resume للاستئناف",
            reply_markup=create_keyboard([
                ("▶️ استئناف", "bot_start"),
                ("🏠 الرئيسية", "back_main")
            ], row_width=2),
            parse_mode="Markdown"
        )

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command"""
        self.bot_manager.resume()
        await update.message.reply_text(
            "✅ **تم استئناف المراقبة**",
            reply_markup=main_menu_keyboard(self.bot_manager.bot_status),
            parse_mode="Markdown"
        )
