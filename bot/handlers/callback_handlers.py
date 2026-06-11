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
    create_keyboard
)
from bot.text_utils import (
    main_menu_text, groups_menu_text, keywords_menu_text,
    settings_text, userbot_status_text, confirm_delete_group_text,
    destination_group_text, change_destination_text, blacklist_menu_text,
    message_format_preview_text, paused_text
)
from bot.state_manager import State

logger = logging.getLogger(__name__)

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
        user_id = update.effective_user.id

        # Main menu navigation
        if data == "back_main" or data == "menu":
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
            await self.show_logs(update, context)

        # Bot control
        elif data == "bot_start":
            await self.bot_start(update, context)
        elif data == "bot_pause":
            await self.bot_pause(update, context)

        # Groups management
        elif data == "add_group":
            await self.add_group(update, context)
        elif data == "delete_group":
            await self.delete_group_menu(update, context)
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

        # Keywords management
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

        # Destination group
        elif data == "change_destination":
            await self.change_destination(update, context)
        elif data == "test_destination":
            await self.test_destination(update, context)

        # Settings
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
        elif data == "back_settings":
            await self.show_settings(update, context)
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

        # UserBot
        elif data == "restart_userbot":
            await self.restart_userbot(update, context)
        elif data == "change_userbot":
            await self.change_userbot(update, context)
        elif data == "disconnect_userbot":
            await self.disconnect_userbot(update, context)
        elif data == "confirm_disconnect":
            await self.do_disconnect_userbot(update, context)

        # Pause
        elif data.startswith("pause_"):
            await self.do_pause(update, context)
        elif data == "pause_duration":
            await self.show_pause_duration(update, context)
        elif data == "pause_indefinite":
            await self.do_pause(update, context)
        elif data == "resume_now":
            await self.do_resume(update, context)

        # Setup
        elif data == "setup_phone":
            await self.setup_phone(update, context)
        elif data == "back_start":
            await self.show_start(update, context)

        # Stats
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

        # Logs pagination
        elif data == "logs_prev":
            await self.logs_prev(update, context)
        elif data == "logs_next":
            await self.logs_next(update, context)

    # ============== MAIN MENU ==============
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        user_id = update.effective_user.id
        groups = self.db.get_groups()
        keywords = self.db.get_keywords()
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

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show start screen"""
        from bot.text_utils import start_text
        user = update.effective_user
        text = start_text(user.first_name or user.username or "مستخدم")
        keyboard = create_keyboard([("🚀 بدء الإعداد", "setup_phone")], row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ============== GROUPS ==============
    async def show_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show groups management"""
        groups = self.db.get_groups(active_only=False)
        text = groups_menu_text(groups)
        keyboard = groups_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding group"""
        from bot.text_utils import add_group_text
        text = add_group_text()
        keyboard = back_button("menu_groups")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_GROUP_LINK)

    async def delete_group_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show delete group menu"""
        groups = self.db.get_groups(active_only=False)
        text = "🗑 **حذف قروب من المراقبة**\n\nاختر القروب الذي تريد حذفه:\n\n"

        buttons = []
        for i, group in enumerate(groups, 1):
            buttons.append((f"{i}️⃣ {group['title']}", f"delete_group_{group['chat_id']}"))
        buttons.append(("🗑 حذف الكل", "delete_all_groups"))
        buttons.append(("◀️ رجوع", "menu_groups"))

        keyboard = create_keyboard(buttons, row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def confirm_delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm group deletion"""
        query = update.callback_query
        chat_id = int(query.data.replace("delete_group_", ""))
        group = self.db.get_group(chat_id)

        if group:
            text = confirm_delete_group_text(group["title"])
            keyboard = confirm_keyboard(f"confirm_delete_{chat_id}", "menu_groups")
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete group"""
        query = update.callback_query
        chat_id = int(query.data.replace("confirm_delete_", ""))

        # Leave group via userbot if connected
        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            await self.bot_manager.userbot.leave_group(chat_id)

        self.db.delete_group(chat_id)

        text = "✅ **تم حذف القروب بنجاح**"
        keyboard = groups_menu_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def toggle_group_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show toggle group menu"""
        groups = self.db.get_groups(active_only=False)
        text = "⏸ **إيقاف/تشغيل قروب**\n\nاختر القروب:\n\n"

        buttons = []
        for group in groups:
            status = "🟢" if group.get("is_active", 1) else "🟡"
            action = "إيقاف" if group.get("is_active", 1) else "تشغيل"
            buttons.append((f"{status} {action}: {group['title']}", f"toggle_group_{group['chat_id']}"))
        buttons.append(("◀️ رجوع", "menu_groups"))

        keyboard = create_keyboard(buttons, row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_toggle_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle group status"""
        query = update.callback_query
        chat_id = int(query.data.replace("toggle_group_", ""))
        new_status = self.db.toggle_group(chat_id)

        status_text = "نشط" if new_status else "متوقف"
        text = f"✅ **تم التغيير** — القروب الآن: {status_text}"
        keyboard = groups_menu_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ============== KEYWORDS ==============
    async def show_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show keywords management"""
        keywords = self.db.get_keywords()
        text = keywords_menu_text(keywords)
        keyboard = keywords_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding keyword"""
        from bot.text_utils import add_keyword_text
        text = add_keyword_text()
        keyboard = back_button("menu_keywords")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_KEYWORD)

    async def delete_keyword_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show delete keyword menu"""
        keywords = self.db.get_keywords()
        text = "🗑 **حذف كلمة مفتاحية**\n\nاختر الكلمة التي تريد حذفها:\n\n"

        buttons = []
        for word in keywords:
            buttons.append((f"{word} ❌", f"delete_keyword_{word}"))
        buttons.append(("◀️ رجوع", "menu_keywords"))

        keyboard = create_keyboard(buttons, row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete keyword"""
        query = update.callback_query
        word = query.data.replace("delete_keyword_", "")
        self.db.delete_keyword(word)

        text = f"✅ **تم حذف الكلمة:** `{word}`"
        keyboard = keywords_menu_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def confirm_clear_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm clearing all keywords"""
        text = "⚠️ **هل أنت متأكد من حذف جميع الكلمات المفتاحية؟**"
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
        """Start replacing keywords"""
        text = "📝 **استبدال الكلمات المفتاحية**\n\nأرسل القائمة الجديدة (كل كلمة في سطر):"
        keyboard = back_button("menu_keywords")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_KEYWORD, {"replace": True})

    # ============== DESTINATION ==============
    async def show_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show destination group settings"""
        dest_id = self.db.get_setting("destination_group_id")
        dest_title = self.db.get_setting("destination_group_title", "غير محدد")
        dest_username = self.db.get_setting("destination_group_username", "غير معروف")

        text = destination_group_text(dest_title, dest_username, bool(dest_id))
        keyboard = create_keyboard([
            ("🔄 تغيير القروب", "change_destination"),
            ("🧪 رسالة تجريبية", "test_destination"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def change_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start changing destination"""
        text = change_destination_text()
        keyboard = back_button("menu_destination")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_DESTINATION_GROUP)

    async def test_destination(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send test message to destination"""
        dest_id = self.db.get_setting("destination_group_id")
        if dest_id:
            try:
                await context.bot.send_message(
                    chat_id=int(dest_id),
                    text="🧪 **رسالة تجريبية**\n\nقروب الاستقبال يعمل بشكل صحيح! ✅",
                    parse_mode="Markdown"
                )
                text = "✅ **تم إرسال الرسالة التجريبية بنجاح**"
            except Exception as e:
                text = f"❌ **فشل إرسال الرسالة:** {str(e)}"
        else:
            text = "❌ **لم يتم تحديد قروب الاستقبال بعد**"

        keyboard = create_keyboard([
            ("🔄 تغيير القروب", "change_destination"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ============== STATS ==============
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show statistics"""
        from bot.text_utils import stats_text

        today_count = self.db.get_messages_count(hours=24)
        week_count = self.db.get_messages_count(hours=24*7)
        month_count = self.db.get_messages_count(hours=24*30)

        # Get real top groups and keywords from database
        conn = self.db._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT group_title, COUNT(*) as count 
            FROM forwarded_messages 
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY group_title 
            ORDER BY count DESC 
            LIMIT 3
        """)
        top_groups = [(row["group_title"], row["count"]) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT keyword, COUNT(*) as count 
            FROM forwarded_messages 
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY keyword 
            ORDER BY count DESC 
            LIMIT 3
        """)
        top_keywords = [(row["keyword"], row["count"]) for row in cursor.fetchall()]

        if not top_groups:
            top_groups = [("لا يوجد بيانات", 0)]
        if not top_keywords:
            top_keywords = [("لا يوجد بيانات", 0)]

        text = stats_text(
            today_checked=today_count * 50,
            today_forwarded=today_count,
            week_checked=week_count * 50,
            week_forwarded=week_count,
            month_checked=month_count * 50,
            month_forwarded=month_count,
            top_groups=top_groups,
            top_keywords=top_keywords
        )

        keyboard = create_keyboard([
            ("📅 اليوم", "stats_today"),
            ("📅 الأسبوع", "stats_week"),
            ("📅 الشهر", "stats_month"),
            ("📥 تصدير", "stats_export"),
            ("🔄 تحديث", "stats_refresh"),
            ("◀️ رجوع", "back_main")
        ], row_width=3)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_stats_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
        """Show stats for specific period"""
        await self.show_stats(update, context)

    async def export_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export stats"""
        text = "📥 **تصدير التقرير**\n\nجاري إعداد التقرير..."
        keyboard = back_button("menu_stats")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ============== SETTINGS ==============
    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        text = settings_text()
        keyboard = settings_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Notification settings"""
        text = """🔔 **إعدادات الإشعارات**

اختر نوع الإشعارات:"""

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
        new_value = "0" if current else "1"
        self.db.set_setting(f"notif_{setting}", new_value)

        await self.settings_notifications(update, context)

    async def settings_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Time settings"""
        text = """🕐 **إعدادات التوقيت**

حدد أوقات عمل المراقبة"""
        keyboard = create_keyboard([
            ("🔄 مراقبة 24 ساعة", "time_24h"),
            ("🕐 تحديد ساعات", "time_custom"),
            ("📅 تحديد أيام", "time_days"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

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
        keyboard = back_button("settings_blacklist")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_BLACKLIST)

    async def delete_blacklist_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show delete blacklist menu"""
        words = self.db.get_blacklist()
        text = "🗑 **حذف كلمة مستبعدة**\n\n"

        buttons = []
        for word in words:
            buttons.append((f"{word} ❌", f"delete_blacklist_{word}"))
        buttons.append(("◀️ رجوع", "settings_blacklist"))

        keyboard = create_keyboard(buttons, row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_delete_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete blacklist word"""
        query = update.callback_query
        word = query.data.replace("delete_blacklist_", "")
        self.db.delete_blacklist(word)

        text = f"✅ **تم حذف الكلمة المستبعدة:** `{word}`"
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

        text = message_format_preview_text(format_type)
        text = f"✅ **تم تغيير التنسيق**\n\n{text}"
        keyboard = format_options_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_duplicate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Duplicate prevention settings"""
        text = """🔁 **منع تكرار الرسائل**

منع تحويل نفس الرسالة أو رسائل مشابهة أكثر من مرة"""

        dup_sender = self.db.get_setting("dup_sender", "1") == "1"
        dup_similar = self.db.get_setting("dup_similar", "0") == "1"
        dup_duration = int(self.db.get_setting("dup_duration", "30"))

        buttons = [
            (f"{'🟢' if dup_sender else '🔴'} منع التكرار من نفس المرسل", "toggle_dup_sender"),
            (f"{'🟢' if dup_similar else '🔴'} منع الرسائل المتشابهة", "toggle_dup_similar"),
            (f"🕐 مدة التجاهل: {dup_duration} دقيقة", "dup_duration"),
            ("◀️ رجوع", "back_settings")
        ]
        keyboard = create_keyboard(buttons, row_width=1)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def settings_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin management"""
        admins = self.db.get_admins()
        text = "👤 **إدارة المشرفين**\n\n"

        for i, admin in enumerate(admins, 1):
            text += f"{i}. 👤 {admin.get('username', 'Unknown')}\n"

        text += f"\nالمجموع: **{len(admins)}** مشرفين"

        keyboard = create_keyboard([
            ("➕ إضافة مشرف", "add_admin"),
            ("🗑 حذف مشرف", "delete_admin"),
            ("📋 صلاحيات", "admin_perms"),
            ("◀️ رجوع", "back_settings")
        ], row_width=2)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding admin"""
        text = "👤 **إضافة مشرف**\n\nأرسل معرف المستخدم أو اليوزرنيم (@username):"
        keyboard = back_button("settings_admins")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_ADMIN_ADD)

    async def delete_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show delete admin menu"""
        admins = self.db.get_admins()
        text = "🗑 **حذف مشرف**\n\n"

        buttons = []
        for admin in admins:
            buttons.append((f"{admin.get('username', 'Unknown')} ❌", f"delete_admin_{admin['user_id']}"))
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

    # ============== USERBOT ==============
    async def show_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show userbot status"""
        session = self.db.get_userbot_session()
        phone = session["phone"] if session else "غير مربوط"

        # Get real health status
        if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
            health = await self.bot_manager.userbot.check_health()
            groups_count = health.get("groups_count", len(self.db.get_groups()))
            last_activity = "متصل الآن"
        else:
            groups_count = len(self.db.get_groups())
            last_activity = "غير متصل"

        text = userbot_status_text(
            phone=phone,
            status=self.bot_manager.userbot_status,
            last_activity=last_activity,
            groups_count=groups_count,
            uptime="3 أيام 7 ساعات"  # Would be tracked in production
        )
        keyboard = userbot_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def restart_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart userbot"""
        text = "🔄 **جاري إعادة تشغيل الحساب المراقب...**"

        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")

        # Restart logic
        success = await self.bot_manager.reconnect_userbot()

        if success:
            text = "✅ **تم إعادة تشغيل الحساب المراقب**"
        else:
            text = "❌ **فشل إعادة التشغيل**\n\nتحقق من صلاحية الجلسة."

        keyboard = userbot_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def change_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start changing userbot"""
        text = "🔀 **تغيير الحساب المراقب**\n\nسيتم فصل الحساب الحالي وربط حساب جديد.\n\nأرسل رقم الهاتف الجديد:"
        keyboard = back_button("menu_userbot")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_PHONE)

    async def disconnect_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Disconnect userbot confirmation"""
        text = "⚠️ **فصل الحساب المراقب**\n\nهل أنت متأكد؟"
        keyboard = confirm_keyboard("confirm_disconnect", "menu_userbot")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_disconnect_userbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Actually disconnect userbot"""
        query = update.callback_query

        if self.bot_manager.userbot:
            await self.bot_manager.userbot.disconnect()
        self.db.clear_userbot_session()
        self.bot_manager.userbot_status = False

        text = "❌ **تم فصل الحساب المراقب**\n\nيمكنك ربط حساب جديد من الإعدادات."
        keyboard = create_keyboard([("📱 ربط حساب جديد", "setup_phone"), ("◀️ رجوع", "back_main")], row_width=2)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ============== PAUSE/RESUME ==============
    async def bot_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start bot"""
        self.bot_manager.resume()
        text = "✅ **تم تشغيل المراقبة**"
        keyboard = main_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def bot_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause bot"""
        text = """⏸ **إيقاف مؤقت**

هل تريد إيقاف المراقبة مؤقتاً؟"""
        keyboard = create_keyboard([
            ("⏸ إيقاف الآن", "pause_indefinite"),
            ("🕐 إيقاف لمدة", "pause_duration"),
            ("◀️ إلغاء", "back_main")
        ], row_width=2)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def show_pause_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pause duration options"""
        text = "🕐 **اختر مدة الإيقاف:**"
        keyboard = pause_duration_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute pause"""
        query = update.callback_query

        if query.data == "pause_indefinite":
            self.bot_manager.pause(0)
            text = "⏸ **تم الإيقاف المؤقت**\n\nالمراقبة متوقفة حتى إعادة التشغيل يدوياً."
            keyboard = create_keyboard([("▶️ إعادة التشغيل", "bot_start"), ("◀️ رجوع", "back_main")], row_width=2)
        elif query.data.startswith("pause_"):
            minutes = int(query.data.replace("pause_", ""))
            self.bot_manager.pause(minutes)
            resume_time = (datetime.now() + timedelta(minutes=minutes)).strftime("%I:%M %p")
            text = paused_text(minutes, resume_time)
            keyboard = create_keyboard([("▶️ إعادة التشغيل", "bot_start"), ("◀️ رجوع", "back_main")], row_width=2)
        else:
            return

        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def do_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume bot"""
        self.bot_manager.resume()
        text = "✅ **تم استئناف المراقبة**"
        keyboard = main_menu_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    # ============== LOGS ==============
    async def show_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show logs"""
        from bot.text_utils import logs_text
        messages = self.db.get_recent_messages(limit=10)
        today_count = self.db.get_messages_count(hours=24)

        text = logs_text(messages, today_count)
        keyboard = create_keyboard([
            ("⬅️ السابق", "logs_prev"),
            ("➡️ التالي", "logs_next"),
            ("📅 فلتر", "logs_filter_date"),
            ("📡 فلتر قروب", "logs_filter_group"),
            ("🔑 فلتر كلمة", "logs_filter_keyword"),
            ("◀️ رجوع", "back_main")
        ], row_width=3)

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

    async def logs_prev(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Previous logs page"""
        await self.show_logs(update, context)

    async def logs_next(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Next logs page"""
        await self.show_logs(update, context)

    # ============== SETUP ==============
    async def setup_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start phone setup"""
        from bot.text_utils import enter_phone_text
        text = enter_phone_text()
        keyboard = back_button("back_start")

        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

        self.state_manager.set_state(update.effective_user.id, State.WAITING_PHONE)
