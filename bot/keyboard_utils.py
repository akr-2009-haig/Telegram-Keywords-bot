# -*- coding: utf-8 -*-
"""Keyboard utilities for creating inline keyboards"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_keyboard(buttons, row_width=2):
    """Create inline keyboard from list of tuples (text, callback_data) or (text, callback_data/url, type)"""
    keyboard = []
    row = []
    for item in buttons:
        if len(item) == 3 and item[2] == "url":
            btn = InlineKeyboardButton(item[0], url=item[1])
        else:
            btn = InlineKeyboardButton(item[0], callback_data=item[1])
        row.append(btn)
        if len(row) >= row_width:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard(bot_running=True):
    """Main menu keyboard — toggle button based on bot status"""
    toggle_btn = ("⏸ إيقاف المراقبة", "bot_pause") if bot_running else ("▶️ تشغيل المراقبة", "bot_start")
    buttons = [
        ("📡 القروبات", "menu_groups"),
        ("🔑 الكلمات المفتاحية", "menu_keywords"),
        ("📥 قروب الاستقبال", "menu_destination"),
        ("📊 الإحصائيات", "menu_stats"),
        ("⚙️ الإعدادات", "menu_settings"),
        ("📱 الحساب المراقب", "menu_userbot"),
        toggle_btn,
        ("📋 سجل الطلبات", "menu_logs"),
    ]
    return create_keyboard(buttons, row_width=2)

def groups_menu_keyboard():
    """Groups management menu"""
    buttons = [
        ("➕ إضافة قروب جديد", "add_group"),
        ("🗑 حذف قروب", "delete_group"),
        ("⏸ إيقاف/تشغيل", "toggle_group"),
        ("🔄 تحديث", "refresh_groups"),
        ("◀️ رجوع", "back_main")
    ]
    return create_keyboard(buttons, row_width=2)

def keywords_menu_keyboard():
    """Keywords management menu"""
    buttons = [
        ("➕ إضافة كلمة", "add_keyword"),
        ("🗑 حذف كلمة", "delete_keyword"),
        ("🗑 حذف الكل", "clear_keywords"),
        ("📝 استبدال الكل", "replace_keywords"),
        ("◀️ رجوع", "back_main")
    ]
    return create_keyboard(buttons, row_width=2)

def settings_menu_keyboard():
    """Settings menu"""
    buttons = [
        ("🔔 الإشعارات", "settings_notifications"),
        ("🕐 التوقيت", "settings_time"),
        ("🚫 كلمات مستبعدة", "settings_blacklist"),
        ("📝 تنسيق الرسالة", "settings_format"),
        ("🔁 التكرار", "settings_duplicate"),
        ("👤 المشرفين", "settings_admins"),
        ("◀️ رجوع", "back_main")
    ]
    return create_keyboard(buttons, row_width=2)

def userbot_menu_keyboard():
    """UserBot management menu"""
    buttons = [
        ("🔄 إعادة تشغيل", "restart_userbot"),
        ("🔀 تغيير الحساب", "change_userbot"),
        ("📡 مراقبة كل القروبات", "monitor_all"),
        ("❌ فصل الحساب", "disconnect_userbot"),
        ("◀️ رجوع", "back_main")
    ]
    return create_keyboard(buttons, row_width=2)

def confirm_keyboard(yes_callback, no_callback):
    """Yes/No confirmation keyboard"""
    buttons = [
        ("✅ نعم", yes_callback),
        ("❌ إلغاء", no_callback)
    ]
    return create_keyboard(buttons, row_width=2)

def pause_duration_keyboard():
    """Pause duration options"""
    buttons = [
        ("30 دقيقة", "pause_30"),
        ("ساعة", "pause_60"),
        ("ساعتين", "pause_120"),
        ("6 ساعات", "pause_360"),
        ("12 ساعة", "pause_720"),
        ("يوم كامل", "pause_1440"),
        ("◀️ رجوع", "back_main")
    ]
    return create_keyboard(buttons, row_width=2)

def format_options_keyboard():
    """Message format options"""
    buttons = [
        ("📋 النموذج الكامل", "format_full"),
        ("📋 النموذج المختصر", "format_short"),
        ("📋 تمرير مباشر", "format_raw"),
        ("◀️ رجوع", "back_settings")
    ]
    return create_keyboard(buttons, row_width=1)

def back_button(callback="back_main"):
    """Single back button"""
    return create_keyboard([("◀️ رجوع", callback)], row_width=1)

def back_and_home_keyboard(back_callback):
    """Back + Home buttons"""
    return create_keyboard([
        ("◀️ رجوع", back_callback),
        ("🏠 الرئيسية", "back_main")
    ], row_width=2)

def forwarded_message_keyboard(record_id, sender_id, sender_username, chat_username=None):
    """Action buttons on forwarded messages in destination group"""
    buttons = []

    # Contact sender button
    if sender_id and sender_id != 0:
        buttons.append((
            "💬 تواصل مع المرسل",
            f"tg://user?id={sender_id}",
            "url"
        ))
    elif sender_username and sender_username.startswith("@"):
        buttons.append((
            "💬 تواصل مع المرسل",
            f"https://t.me/{sender_username[1:]}",
            "url"
        ))

    buttons.append(("✅ تم الأخذ", f"order_taken_{record_id}"))
    buttons.append(("🚫 تجاهل", f"order_ignore_{record_id}"))

    if chat_username:
        buttons.append((
            "📡 فتح القروب",
            f"https://t.me/{chat_username}",
            "url"
        ))

    return create_keyboard(buttons, row_width=2)

def logs_keyboard(page=0, total=0, per_page=10):
    """Logs navigation keyboard"""
    buttons = []

    has_prev = page > 0
    has_next = (page + 1) * per_page < total

    nav = []
    if has_prev:
        nav.append(("⬅️ السابق", f"logs_page_{page - 1}"))
    if has_next:
        nav.append(("➡️ التالي", f"logs_page_{page + 1}"))
    if nav:
        buttons.extend(nav)

    buttons.extend([
        ("📅 فلتر بالتاريخ", "logs_filter_date"),
        ("📡 فلتر بالقروب", "logs_filter_group"),
        ("🔑 فلتر بالكلمة", "logs_filter_keyword"),
        ("◀️ رجوع", "back_main")
    ])
    return create_keyboard(buttons, row_width=2)
