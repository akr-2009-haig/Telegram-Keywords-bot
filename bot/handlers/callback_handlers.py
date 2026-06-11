# -*- coding: utf-8 -*-
"""Callback query handlers for inline keyboard buttons"""

import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from bot.keyboard_utils import (
    main_menu_keyboard, groups_menu_keyboard, keywords_menu_keyboard,
    settings_menu_keyboard, userbot_menu_keyboard, confirm_keyboard,
    pause_duration_keyboard, format_options_keyboard, back_button,
    back_and_home_keyboard, create_keyboard, logs_keyboard
)
from bot.text_utils import (
    main_menu_text, groups_menu_text, keywords_menu_text,
    settings_text, userbot_status_text, confirm_delete_group_text,
    destination_group_text, change_destination_text, blacklist_menu_text,
    message_format_preview_text, paused_text, start_text
)
from bot.state_manager import State

logger = logging.getLogger(__name__)

LOGS_PER_PAGE = 10


class CallbackHandlers:
    """Handle all callback queries"""

    @staticmethod
    def setup(application, db, state_manager, bot_manager):
        """Register all callback handlers"""
        handlers = CallbackHandlers(db, state_manager, bot_manager)
        application.add_handler(CallbackQueryHandler(handlers.handle_callback))

    def __init__(self, db, state_manager, bot_manager):
        self.db = db
        self.state_manager = state_manager
        self.bot_manager = bot_manager

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main callback dispatcher"""
        query = update.callback_query
        await query.answer()

        data = query.data

        # ── Main navigation ──────────────────────────────────────
        if data in ("back_main", "menu"):
            await self.show_main_menu(update, context)
        elif data == "menu_groups":
            await self.show_groups(update, context)
        elif data == "menu_keywords":
            await self.show_keywords(update, context)
        elif data == "menu_destination":
            await self.show_destination(update, context)
        elif data == "menu_stats":
            await self.show_stats(update, context)
        elif data == "menu_settings":
            await self.show_settings(update, context)
        elif data == "menu_userbot":
            await self.show_userbot(update, context)
        elif data == "menu_logs":
            await self.show_logs(update, context, page=0)
        elif data == "help":
            await self.show_help(update, context)

        # ── Bot control ──────────────────────────────────────────
        elif data == "bot_start":
            await self.bot_start(update, context)
        elif data == "bot_pause":
            await self.bot_pause(update, context)

        # ── Groups ───────────────────────────────────────────────
        elif data == "add_group":
            await self.add_group(update, context)
        elif data == "delete_group":
            await self.delete_group_menu(update, context)
        elif data == "delete_all_groups":
            await self.confirm_delete_all_groups(update, context)
        elif data == "confirm_delete_all_groups":
            await self.do_delete_all_groups(update, context)
        elif data == "toggle_group":
            await self.toggle_group_menu(update, context)
        elif data == "refresh_groups":
            await self.show_groups(update, context)
        elif data.startswith("delete_group_"):
            await self.confirm_delete_group(update, context)
        elif data.startswith("confirm_delete_"):
            await self.do_delete_group(update, context)
        elif data.startswith("toggle_group_"):
            await self.do_toggle_group(update, context)

        # ── Keywords ─────────────────────────────────────────────
        elif data == "add_keyword":
            await self.add_keyword(update, context)
        elif data == "delete_keyword":
            await self.delete_keyword_menu(update, context)
        elif data == "clear_keywords":
            await self.confirm_clear_keywords(update, context)
        elif data == "replace_keywords":
            await self.replace_keywords(update, context)
        elif data.startswith("delete_keyword_"):
            await self.do_delete_keyword(update, context)
        elif data == "confirm_clear_keywords":
            await self.do_clear_keywords(update, context)

        # ── Destination group ─────────────────────────────────────
        elif data == "change_destination":
            await self.change_destination(update, context)
        elif data == "test_destination":
            await self.test_destination(update, context)

        # ── Settings ──────────────────────────────────────────────
        elif data == "back_settings":
            await self.show_settings(update, context)
        elif data == "settings_notifications":
            await self.settings_notifications(update, context)
        elif data == "settings_time":
            await self.settings_time(update, context)
        elif data == "settings_blacklist":
            await self.settings_blacklist(update, context)
        elif data == "settings_format":
            await self.settings_format(update, context)
        elif data == "settings_duplicate":
            await self.settings_duplicate(update, context)
        elif data == "settings_admins":
            await self.settings_admins(update, context)
        elif data.startswith("toggle_notif_"):
            await self.toggle_notification(update, context)
        elif data.startswith("format_"):
            await self.set_format(update, context)
        elif data == "add_blacklist":
            await self.add_blacklist(update, context)
        elif data == "delete_blacklist":
            await self.delete_blacklist_menu(update, context)
        elif data.startswith("delete_blacklist_"):
            await self.do_delete_blacklist(update, context)
        elif data == "add_admin":
            await self.add_admin(update, context)
        elif data == "delete_admin":
            await self.delete_admin_menu(update, context)
        elif data.startswith("delete_admin_"):
            await self.do_delete_admin(update, context)
        elif data == "admin_perms":
            await self.admin_perms(update, context)

        # ── Duplicate prevention ───────────────────────────────────
        elif data == "toggle_dup_sender":
            await self.toggle_dup_setting(update, context, "dup_sender")
        elif data == "toggle_dup_similar":
            await self.toggle_dup_setting(update, context, "dup_similar")
        elif data == "dup_duration":
            await self.set_dup_duration(update, context)

        # ── Time settings ──────────────────────────────────────────
        elif data == "time_24h":
            await self.set_time_mode(update, context, "24h")
        elif data == "time_custom":
            await self.set_time_mode(update, context, "custom")
        elif data == "time_days":
            await self.set_time_mode(update, context, "days")

        # ── UserBot ────────────────────────────────────────────────
        elif data == "restart_userbot":
            await self.restart_userbot(update, context)
        elif data == "change_userbot":
            await self.change_userbot(update, context)
        elif data == "disconnect_userbot":
            await self.disconnect_userbot(update, context)
        elif data == "confirm_disconnect":
            await self.do_disconnect_userbot(update, context)

        # ── Pause/Resume  — IMPORTANT: specific checks BEFORE startswith ──
        elif data == "pause_duration":
            await self.show_pause_duration(update, context)
        elif data == "pause_indefinite":
            await self.do_pause(update, context)
        elif data == "resume_now":
            await self.do_resume(update, context)
        elif data.startswith("pause_"):
            await self.do_pause(update, context)

        # ── Setup ─────────────────────────────────────────────────
        elif data == "setup_phone":
            await self.setup_phone(update, context)
        elif data == "back_start":
            await self.show_start(update, context)

        # ── Stats ──────────────────────────────────────────────────
        elif data == "stats_today":
            await self.show_stats_period(update, context, 1)
        elif data == "stats_week":
            await self.show_stats_period(update, context, 7)
        elif data == "stats_month":
            await self.show_stats_period(update, context, 30)
        elif data == "stats_export":
            await self.export_stats(update, context)
        elif data == "stats_refresh":
            await self.show_stats(update, context)

        # ── Logs ───────────────────────────────────────────────────
        elif data.startswith("logs_page_"):
            page = int(data.replace("logs_page_", ""))
            await self.show_logs(update, context, page=page)
        elif data == "logs_filter_date":
            await self.logs_filter_stub(update, context, "بالتاريخ")
        elif data == "logs_filter_group":
            await self.logs_filter_stub(update, context, "بالقروب")
        elif data == "logs_filter_keyword":
            await self.logs_filter_stub(update, context, "بالكلمة المفتاحية")

        # ── Order actions (buttons on forwarded messages) ──────────
        elif data.startswith("order_taken_"):
            await self.order_taken(update, context)
        elif data.startswith("order_ignore_"):
            await self.order_ignore(update, context)

        else:
            logger.warning(f"Unhandled callback: {data}")

    # ═══════════════════════════════════════════════════════════════
    # MAIN MENU
    # ═══════════════════════════════════════════════════════════════

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        groups_count = len(self.db.get_groups(active_only=True))
        keywords_count = len(self.db.get_keywords())
        today_count = self.db.get_messages_count(hours=24)

        recent = self.db.get_recent_messages(limit=1)
        last_time = "لا يوجد"
        if recent:
            try:
                last_dt = datetime.fromisoformat(recent[0]["created_at"])
                diff = datetime.now() - last_dt
                if diff.total_seconds() < 60:
                    last_time = f"{int(diff.total_seconds())} ثانية"
                elif diff.total_seconds() < 3600:
                    last_time = f"{int(diff.total_seconds() / 60)} دقيقة"
                else:
                    last_time = f"{int(diff.total_seconds() / 3600)} ساعة"
            except Exception:
                last_time = "غير معروف"

        text = main_menu_text(
            bot_running=self.bot_manager.bot_status,
            userbot_connected=self.bot_manager.userbot_status,
            groups_count=groups_count,
            keywords_count=keywords_count,
            today_orders=today_count,
            last_order_time=last_time
        )
        keyboard = main_menu_keyboard(self.bot_manager.bot_status)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show start/welcome screen"""
        text = start_text()
        keyboard = create_keyboard([
            ("🚀 بدء الإعداد", "setup_phone"),
            ("🏠 الرئيسية", "back_main")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help screen"""
        from bot.text_utils import help_text
        keyboard = back_and_home_keyboard("back_main")
        if update.callback_query:
            await update.callback_query.edit_message_text(help_text(), reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(help_text(), reply_markup=keyboard, parse_mode="Markdown")

    # ═══════════════════════════════════════════════════════════════
    # GROUPS
    # ═══════════════════════════════════════════════════════════════

    async def show_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show groups management"""
        groups = self.db.get_groups(active_only=False)
        text = groups_menu_text(groups)
        keyboard = groups_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt for group link"""
        text = """➕ **إضافة قروب جديد**

أرسل رابط أو معرف القروب:

**أنواع الروابط المقبولة:**
• `https://t.me/group_name`
• `https://t.me/+InviteHash`
• `@group_name`

يمكن إرسال عدة روابط في رسالة واحدة (كل رابط في سطر)"""
        keyboard = back_and_home_keyboard("menu_groups")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_GROUP_LINK)

    async def delete_group_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show group deletion menu"""
        groups = self.db.get_groups(active_only=False)
        if not groups:
            text = "📭 **لا توجد قروبات مضافة**"
            keyboard = back_and_home_keyboard("menu_groups")
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
            return

        text = "🗑 **اختر قروباً لحذفه:**\n\n"
        buttons = []
        for g in groups:
            label = g.get("title", "Unknown")[:25]
            buttons.append((f"❌ {label}", f"delete_group_{g['chat_id']}"))

        buttons.append(("🗑 حذف الكل", "delete_all_groups"))
        buttons.append(("◀️ رجوع", "menu_groups"))
        keyboard = create_keyboard(buttons, row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def confirm_delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm single group deletion"""
        query = update.callback_query
        chat_id = query.data.replace("delete_group_", "")
        try:
            chat_id_int = int(chat_id)
        except ValueError:
            return

        group = self.db.get_group(chat_id_int)
        title = group["title"] if group else "Unknown"

        text = confirm_delete_group_text(title)
        keyboard = confirm_keyboard(f"confirm_delete_{chat_id}", "delete_group")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete single group"""
        query = update.callback_query
        chat_id = query.data.replace("confirm_delete_", "")
        try:
            chat_id_int = int(chat_id)
        except ValueError:
            return

        group = self.db.get_group(chat_id_int)
        title = group["title"] if group else "Unknown"
        self.db.delete_group(chat_id_int)

        # Restart monitoring without deleted group
        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            groups = self.db.get_groups(active_only=True)
            await self.bot_manager.userbot.start_monitoring(groups)

        text = f"✅ **تم حذف القروب:** {title}"
        keyboard = groups_menu_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def confirm_delete_all_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm deleting all groups"""
        text = "⚠️ **حذف جميع القروبات**\n\nهل أنت متأكد؟ سيتم إيقاف المراقبة لجميع القروبات."
        keyboard = confirm_keyboard("confirm_delete_all_groups", "menu_groups")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_all_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete all groups"""
        self.db.delete_all_groups()
        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            await self.bot_manager.userbot.stop_monitoring()

        text = "✅ **تم حذف جميع القروبات**\n\nأضف قروبات جديدة لبدء المراقبة."
        keyboard = groups_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def toggle_group_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show toggle group menu"""
        groups = self.db.get_groups(active_only=False)
        if not groups:
            text = "📭 **لا توجد قروبات مضافة**"
            keyboard = back_and_home_keyboard("menu_groups")
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
            return

        text = "⏸ **تشغيل/إيقاف قروب:**"
        buttons = []
        for g in groups:
            status_icon = "🟢" if g.get("is_active", 1) else "🔴"
            label = g.get("title", "Unknown")[:22]
            buttons.append((f"{status_icon} {label}", f"toggle_group_{g['chat_id']}"))
        buttons.append(("◀️ رجوع", "menu_groups"))
        keyboard = create_keyboard(buttons, row_width=1)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_toggle_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle group active status"""
        query = update.callback_query
        chat_id = int(query.data.replace("toggle_group_", ""))
        new_status = self.db.toggle_group(chat_id)

        group = self.db.get_group(chat_id)
        title = group["title"] if group else "Unknown"
        status_str = "🟢 مفعّل" if new_status else "🔴 موقف"

        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            groups = self.db.get_groups(active_only=True)
            await self.bot_manager.userbot.start_monitoring(groups)

        text = f"✅ **{title}**\nالحالة: {status_str}"
        keyboard = groups_menu_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ═══════════════════════════════════════════════════════════════
    # KEYWORDS
    # ═══════════════════════════════════════════════════════════════

    async def show_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show keywords management"""
        words = self.db.get_keywords()
        text = keywords_menu_text(words)
        keyboard = keywords_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt for keyword"""
        text = "➕ **إضافة كلمة مفتاحية**\n\nأرسل الكلمة أو الكلمات (كل كلمة في سطر جديد):"
        keyboard = back_and_home_keyboard("menu_keywords")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_KEYWORD)

    async def delete_keyword_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show keyword deletion menu"""
        words = self.db.get_keywords()
        if not words:
            text = "📭 **لا توجد كلمات مفتاحية**"
            keyboard = back_and_home_keyboard("menu_keywords")
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
            return

        text = "🗑 **اختر كلمة لحذفها:**"
        buttons = [(f"❌ {w}", f"delete_keyword_{w}") for w in words]
        buttons.append(("◀️ رجوع", "menu_keywords"))
        keyboard = create_keyboard(buttons, row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete keyword"""
        query = update.callback_query
        word = query.data.replace("delete_keyword_", "")
        self.db.delete_keyword(word)
        words = self.db.get_keywords()
        text = keywords_menu_text(words)
        keyboard = keywords_menu_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def confirm_clear_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm clearing all keywords"""
        text = "⚠️ **حذف جميع الكلمات المفتاحية**\n\nهل أنت متأكد؟"
        keyboard = confirm_keyboard("confirm_clear_keywords", "menu_keywords")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_clear_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear all keywords"""
        self.db.clear_keywords()
        text = "✅ **تم حذف جميع الكلمات المفتاحية**"
        keyboard = keywords_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def replace_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Replace all keywords"""
        text = "📝 **استبدال جميع الكلمات المفتاحية**\n\nأرسل الكلمات الجديدة (كل كلمة في سطر):\n\n⚠️ سيتم حذف الكلمات القديمة"
        keyboard = back_and_home_keyboard("menu_keywords")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_KEYWORD,
                                     data={"replace": True})

    # ═══════════════════════════════════════════════════════════════
    # DESTINATION GROUP
    # ═══════════════════════════════════════════════════════════════

    async def show_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show destination group settings"""
        dest_id = self.db.get_setting("destination_group_id")
        dest_title = self.db.get_setting("destination_group_title", "غير محدد")
        dest_username = self.db.get_setting("destination_group_username", "")
        is_set = bool(dest_id)

        text = destination_group_text(dest_title, dest_username, is_set)
        keyboard = create_keyboard([
            ("🔄 تغيير القروب", "change_destination"),
            ("🧪 رسالة تجريبية", "test_destination"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def change_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt for new destination group"""
        text = change_destination_text()
        keyboard = back_and_home_keyboard("menu_destination")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_DESTINATION_GROUP)

    async def test_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send test message to destination group"""
        dest_id = self.db.get_setting("destination_group_id")
        if not dest_id:
            if update.callback_query:
                await update.callback_query.answer("❌ لم يتم تحديد قروب الاستقبال", show_alert=True)
            return

        try:
            test_text = (
                "🧪 **رسالة تجريبية**\n\n"
                "✅ البوت يعمل بشكل صحيح\n"
                f"⏱ {datetime.now().strftime('%H:%M — %d/%m/%Y')}"
            )
            await context.bot.send_message(
                chat_id=int(dest_id),
                text=test_text,
                parse_mode="Markdown"
            )
            if update.callback_query:
                await update.callback_query.answer("✅ تم إرسال الرسالة التجريبية!", show_alert=True)
        except Exception as e:
            if update.callback_query:
                await update.callback_query.answer(f"❌ فشل: {str(e)}", show_alert=True)

    # ═══════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show statistics menu"""
        from bot.text_utils import stats_text
        stats = self.db.get_stats(days=30)
        today_count = self.db.get_messages_count(hours=24)
        groups_count = len(self.db.get_groups(active_only=True))
        keywords_count = len(self.db.get_keywords())
        uptime = self.bot_manager.get_uptime()

        text = stats_text(
            today=today_count,
            total=stats["total_forwarded"],
            checked=stats["total_checked"],
            groups_count=groups_count,
            keywords_count=keywords_count,
            uptime=uptime
        )
        keyboard = create_keyboard([
            ("📅 اليوم", "stats_today"),
            ("📅 هذا الأسبوع", "stats_week"),
            ("📅 هذا الشهر", "stats_month"),
            ("🔄 تحديث", "stats_refresh"),
            ("📤 تصدير", "stats_export"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_stats_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
        """Show stats for specific period"""
        stats = self.db.get_stats(days=days)
        period_label = {1: "اليوم", 7: "الأسبوع", 30: "الشهر"}.get(days, f"{days} يوم")

        text = (
            f"📊 **إحصائيات {period_label}**\n\n"
            f"📨 رسائل فُحصت: **{stats['total_checked']:,}**\n"
            f"📤 طلبات حُوّلت: **{stats['total_forwarded']:,}**\n"
            f"📅 أيام النشاط: **{stats['days_active']}**\n"
        )
        keyboard = create_keyboard([
            ("📅 اليوم", "stats_today"),
            ("📅 الأسبوع", "stats_week"),
            ("📅 الشهر", "stats_month"),
            ("◀️ رجوع", "menu_stats")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def export_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export statistics as text"""
        stats_30 = self.db.get_stats(days=30)
        stats_7 = self.db.get_stats(days=7)
        today_count = self.db.get_messages_count(hours=24)

        text = (
            f"📊 **تقرير الإحصائيات**\n"
            f"🕐 {datetime.now().strftime('%H:%M — %d/%m/%Y')}\n\n"
            f"**اليوم:** {today_count} طلب\n"
            f"**الأسبوع:** {stats_7['total_forwarded']} طلب\n"
            f"**الشهر:** {stats_30['total_forwarded']} طلب\n\n"
            f"**إجمالي مفحوص (30 يوم):** {stats_30['total_checked']:,}\n"
        )
        keyboard = create_keyboard([("◀️ رجوع", "menu_stats")], row_width=1)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ═══════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        text = settings_text()
        keyboard = settings_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Notification settings"""
        text = "🔔 **إعدادات الإشعارات**\n\nاختر نوع الإشعارات:"

        notif_all = self.db.get_setting("notif_all", "1") == "1"
        notif_hourly = self.db.get_setting("notif_hourly", "0") == "1"
        notif_stop = self.db.get_setting("notif_stop", "1") == "1"
        notif_join = self.db.get_setting("notif_join", "0") == "1"

        buttons = [
            (f"{'🟢' if notif_all else '🔴'} إشعار عند كل طلب", "toggle_notif_all"),
            (f"{'🟢' if notif_hourly else '🔴'} ملخص كل ساعة", "toggle_notif_hourly"),
            (f"{'🟢' if notif_stop else '🔴'} تنبيه عند التوقف", "toggle_notif_stop"),
            (f"{'🟢' if notif_join else '🔴'} تنبيه الانضمام/الطرد", "toggle_notif_join"),
            ("◀️ رجوع", "back_settings")
        ]
        keyboard = create_keyboard(buttons, row_width=1)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def toggle_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle notification setting"""
        query = update.callback_query
        setting = query.data.replace("toggle_notif_", "")
        current = self.db.get_setting(f"notif_{setting}", "0") == "1"
        self.db.set_setting(f"notif_{setting}", "0" if current else "1")
        await self.settings_notifications(update, context)

    async def settings_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Time settings"""
        current_mode = self.db.get_setting("time_mode", "24h")
        mode_labels = {"24h": "مراقبة 24 ساعة ✅", "custom": "ساعات محددة ✅", "days": "أيام محددة ✅"}

        text = f"🕐 **إعدادات التوقيت**\n\nالوضع الحالي: **{mode_labels.get(current_mode, '24 ساعة')}**\n\nحدد أوقات عمل المراقبة:"
        keyboard = create_keyboard([
            ("🔄 مراقبة 24 ساعة", "time_24h"),
            ("🕐 تحديد ساعات", "time_custom"),
            ("📅 تحديد أيام", "time_days"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def set_time_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
        """Set monitoring time mode"""
        self.db.set_setting("time_mode", mode)
        labels = {"24h": "مراقبة 24 ساعة", "custom": "ساعات محددة", "days": "أيام محددة"}
        if update.callback_query:
            await update.callback_query.answer(f"✅ تم التعيين: {labels.get(mode, mode)}", show_alert=True)
        await self.settings_time(update, context)

    async def settings_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Blacklist settings"""
        words = self.db.get_blacklist()
        text = blacklist_menu_text(words)
        keyboard = create_keyboard([
            ("➕ إضافة كلمة", "add_blacklist"),
            ("🗑 حذف كلمة", "delete_blacklist"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding blacklist word"""
        text = "🚫 **إضافة كلمة مستبعدة**\n\nأرسل الكلمة التي تريد استبعادها:"
        keyboard = back_and_home_keyboard("settings_blacklist")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_BLACKLIST)

    async def delete_blacklist_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show delete blacklist menu"""
        words = self.db.get_blacklist()
        if not words:
            if update.callback_query:
                await update.callback_query.answer("📭 لا توجد كلمات مستبعدة", show_alert=True)
            return

        text = "🗑 **حذف كلمة مستبعدة:**"
        buttons = [(f"{w} ❌", f"delete_blacklist_{w}") for w in words]
        buttons.append(("◀️ رجوع", "settings_blacklist"))
        keyboard = create_keyboard(buttons, row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete blacklist word"""
        query = update.callback_query
        word = query.data.replace("delete_blacklist_", "")
        self.db.delete_blacklist(word)
        text = f"✅ **تم حذف الكلمة:** `{word}`"
        keyboard = create_keyboard([
            ("➕ إضافة كلمة", "add_blacklist"),
            ("🗑 حذف كلمة", "delete_blacklist"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Message format settings"""
        current_format = self.db.get_setting("message_format", "full")
        text = message_format_preview_text(current_format)
        keyboard = format_options_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def set_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set message format"""
        query = update.callback_query
        format_type = query.data.replace("format_", "")
        self.db.set_setting("message_format", format_type)
        text = f"✅ **تم تغيير التنسيق**\n\n{message_format_preview_text(format_type)}"
        keyboard = format_options_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_duplicate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Duplicate prevention settings"""
        dup_sender = self.db.get_setting("dup_sender", "1") == "1"
        dup_similar = self.db.get_setting("dup_similar", "0") == "1"
        dup_duration = int(self.db.get_setting("dup_duration", "30"))

        text = (
            f"🔁 **منع تكرار الرسائل**\n\n"
            f"منع تحويل نفس الرسالة أو رسائل مشابهة أكثر من مرة\n\n"
            f"مدة التجاهل الحالية: **{dup_duration} دقيقة**"
        )
        buttons = [
            (f"{'🟢' if dup_sender else '🔴'} منع التكرار من نفس المرسل", "toggle_dup_sender"),
            (f"{'🟢' if dup_similar else '🔴'} منع الرسائل المتشابهة", "toggle_dup_similar"),
            (f"🕐 مدة التجاهل: {dup_duration} دقيقة", "dup_duration"),
            ("◀️ رجوع", "back_settings")
        ]
        keyboard = create_keyboard(buttons, row_width=1)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def toggle_dup_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
        """Toggle a duplicate prevention setting"""
        current = self.db.get_setting(key, "0") == "1"
        self.db.set_setting(key, "0" if current else "1")
        await self.settings_duplicate(update, context)

    async def set_dup_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show duration options for duplicate prevention"""
        text = "🕐 **اختر مدة التجاهل:**\n\nالرسائل المتكررة خلال هذه المدة ستُتجاهل"
        buttons = [
            ("15 دقيقة", "dup_dur_15"),
            ("30 دقيقة", "dup_dur_30"),
            ("ساعة", "dup_dur_60"),
            ("ساعتين", "dup_dur_120"),
            ("6 ساعات", "dup_dur_360"),
            ("◀️ رجوع", "settings_duplicate")
        ]
        keyboard = create_keyboard(buttons, row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin management"""
        admins = self.db.get_admins()
        text = "👤 **إدارة المشرفين**\n\n"
        if admins:
            for i, admin in enumerate(admins, 1):
                text += f"{i}. 👤 @{admin.get('username', 'Unknown')}\n"
            text += f"\nالمجموع: **{len(admins)}** مشرفين"
        else:
            text += "لا يوجد مشرفين مضافين"

        keyboard = create_keyboard([
            ("➕ إضافة مشرف", "add_admin"),
            ("🗑 حذف مشرف", "delete_admin"),
            ("📋 الصلاحيات", "admin_perms"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding admin"""
        text = "👤 **إضافة مشرف**\n\nأرسل معرف المستخدم أو اليوزرنيم (@username):"
        keyboard = back_and_home_keyboard("settings_admins")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_ADMIN_ADD)

    async def delete_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show delete admin menu"""
        admins = self.db.get_admins()
        if not admins:
            if update.callback_query:
                await update.callback_query.answer("📭 لا يوجد مشرفين", show_alert=True)
            return

        text = "🗑 **حذف مشرف:**"
        buttons = [(f"@{a.get('username', 'Unknown')} ❌", f"delete_admin_{a['user_id']}") for a in admins]
        buttons.append(("◀️ رجوع", "settings_admins"))
        keyboard = create_keyboard(buttons, row_width=1)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete admin"""
        query = update.callback_query
        admin_id = int(query.data.replace("delete_admin_", ""))
        self.db.delete_admin(admin_id)
        text = "✅ **تم حذف المشرف**"
        keyboard = create_keyboard([
            ("➕ إضافة مشرف", "add_admin"),
            ("🗑 حذف مشرف", "delete_admin"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def admin_perms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin permissions info"""
        text = (
            "📋 **صلاحيات المشرفين**\n\n"
            "المشرفون لديهم الصلاحيات التالية:\n"
            "• 👀 عرض الإحصائيات والسجلات\n"
            "• 📡 إضافة/حذف القروبات\n"
            "• 🔑 إدارة الكلمات المفتاحية\n"
            "• ⏸ إيقاف/تشغيل المراقبة\n\n"
            "⚠️ المالك فقط يستطيع:\n"
            "• إضافة/حذف مشرفين\n"
            "• تغيير الحساب المراقب\n"
            "• تغيير إعدادات الإشعارات"
        )
        keyboard = back_and_home_keyboard("settings_admins")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ═══════════════════════════════════════════════════════════════
    # USERBOT
    # ═══════════════════════════════════════════════════════════════

    async def show_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show userbot status"""
        session = self.db.get_userbot_session()
        phone = session["phone"] if session else "غير مربوط"

        groups_count = len(self.db.get_groups(active_only=True))
        last_activity = "متصل" if self.bot_manager.userbot_status else "غير متصل"

        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            try:
                health = await self.bot_manager.userbot.check_health()
                groups_count = health.get("groups_count", groups_count)
            except Exception:
                pass

        uptime = self.bot_manager.get_uptime()

        text = userbot_status_text(
            phone=phone,
            status=self.bot_manager.userbot_status,
            last_activity=last_activity,
            groups_count=groups_count,
            uptime=uptime
        )
        keyboard = userbot_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def restart_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart userbot"""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "🔄 **جاري إعادة تشغيل الحساب المراقب...**",
                parse_mode="Markdown"
            )
        success = await self.bot_manager.reconnect_userbot()
        text = "✅ **تم إعادة تشغيل الحساب المراقب**" if success else "❌ **فشل إعادة التشغيل**\n\nتحقق من صلاحية الجلسة."
        keyboard = userbot_menu_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def change_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start changing userbot"""
        text = "🔀 **تغيير الحساب المراقب**\n\nسيتم فصل الحساب الحالي.\n\nأرسل رقم الهاتف الجديد بالصيغة الدولية:"
        keyboard = back_and_home_keyboard("menu_userbot")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_PHONE)

    async def disconnect_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disconnect userbot confirmation"""
        text = "⚠️ **فصل الحساب المراقب**\n\nهل أنت متأكد؟ سيتوقف البوت عن المراقبة."
        keyboard = confirm_keyboard("confirm_disconnect", "menu_userbot")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_disconnect_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Actually disconnect userbot"""
        if self.bot_manager.userbot:
            try:
                await self.bot_manager.userbot.disconnect()
            except Exception:
                pass
        self.db.clear_userbot_session()
        self.bot_manager.userbot_status = False

        text = "❌ **تم فصل الحساب المراقب**\n\nيمكنك ربط حساب جديد من الإعدادات."
        keyboard = create_keyboard([
            ("📱 ربط حساب جديد", "setup_phone"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ═══════════════════════════════════════════════════════════════
    # PAUSE / RESUME
    # ═══════════════════════════════════════════════════════════════

    async def bot_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume monitoring"""
        self.bot_manager.resume()
        text = "✅ **تم تشغيل المراقبة**"
        keyboard = main_menu_keyboard(True)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def bot_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pause options"""
        text = "⏸ **إيقاف مؤقت**\n\nهل تريد إيقاف المراقبة مؤقتاً؟"
        keyboard = create_keyboard([
            ("⏸ إيقاف الآن", "pause_indefinite"),
            ("🕐 إيقاف لمدة محددة", "pause_duration"),
            ("◀️ إلغاء", "back_main")
        ], row_width=1)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_pause_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pause duration options"""
        text = "🕐 **اختر مدة الإيقاف:**"
        keyboard = pause_duration_keyboard()
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute pause with specific duration"""
        query = update.callback_query

        if query.data == "pause_indefinite":
            self.bot_manager.pause(0)
            text = "⏸ **تم الإيقاف المؤقت**\n\nالمراقبة متوقفة حتى إعادة التشغيل يدوياً."
        else:
            try:
                minutes = int(query.data.replace("pause_", ""))
            except ValueError:
                return
            self.bot_manager.pause(minutes)
            resume_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%I:%M %p")
            text = paused_text(minutes, resume_time)

        keyboard = create_keyboard([
            ("▶️ إعادة التشغيل", "bot_start"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume monitoring"""
        self.bot_manager.resume()
        text = "✅ **تم استئناف المراقبة**"
        keyboard = main_menu_keyboard(True)
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ═══════════════════════════════════════════════════════════════
    # LOGS
    # ═══════════════════════════════════════════════════════════════

    async def show_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """Show forwarded messages log with pagination"""
        from bot.text_utils import logs_text
        total = self.db.get_total_messages_count()
        offset = page * LOGS_PER_PAGE
        messages = self.db.get_recent_messages(limit=LOGS_PER_PAGE, offset=offset)
        today_count = self.db.get_messages_count(hours=24)

        text = logs_text(messages, today_count, page=page, total=total, per_page=LOGS_PER_PAGE)
        keyboard = logs_keyboard(page=page, total=total, per_page=LOGS_PER_PAGE)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def logs_filter_stub(self, update: Update, context: ContextTypes.DEFAULT_TYPE, filter_type: str):
        """Placeholder for log filtering — shows coming soon"""
        if update.callback_query:
            await update.callback_query.answer(
                f"🔄 الفلترة {filter_type} قادمة في التحديث القادم",
                show_alert=True
            )

    # ═══════════════════════════════════════════════════════════════
    # ORDER ACTIONS (buttons on forwarded messages)
    # ═══════════════════════════════════════════════════════════════

    async def order_taken(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark order as taken"""
        query = update.callback_query
        try:
            record_id = int(query.data.replace("order_taken_", ""))
        except ValueError:
            await query.answer("❌ خطأ في البيانات", show_alert=True)
            return

        self.db.update_forwarded_message_status(record_id, "taken")
        taker = update.effective_user
        taker_name = f"@{taker.username}" if taker.username else taker.first_name or "مستخدم"

        # Edit the message to show it's been taken
        try:
            original_text = query.message.text or ""
            new_text = f"✅ **تم الأخذ** بواسطة {taker_name}\n\n{original_text}"
            taken_keyboard = create_keyboard([
                ("✅ تم الأخذ ✓", f"order_taken_{record_id}"),
            ], row_width=1)
            await query.edit_message_reply_markup(reply_markup=taken_keyboard)
        except Exception:
            pass

        await query.answer("✅ تم تحديد الطلب كمأخوذ!", show_alert=True)

    async def order_ignore(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark order as ignored"""
        query = update.callback_query
        try:
            record_id = int(query.data.replace("order_ignore_", ""))
        except ValueError:
            await query.answer("❌ خطأ في البيانات", show_alert=True)
            return

        self.db.update_forwarded_message_status(record_id, "ignored")

        try:
            ignore_keyboard = create_keyboard([
                ("🚫 تم التجاهل", f"order_ignore_{record_id}"),
            ], row_width=1)
            await query.edit_message_reply_markup(reply_markup=ignore_keyboard)
        except Exception:
            pass

        await query.answer("🚫 تم تحديد الطلب كمتجاهل", show_alert=True)

    # ═══════════════════════════════════════════════════════════════
    # SETUP
    # ═══════════════════════════════════════════════════════════════

    async def setup_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start phone setup"""
        from bot.text_utils import enter_phone_text
        text = enter_phone_text()
        keyboard = back_and_home_keyboard("back_start")
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.set_state(update.effective_user.id, State.WAITING_PHONE)
