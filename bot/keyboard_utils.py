# -*- coding: utf-8 -*-
"""Keyboard utilities for creating inline keyboards"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_keyboard(buttons, row_width=2):
    """Create inline keyboard from list of tuples (text, callback_data)"""
    keyboard = []
    row = []
    for text, callback in buttons:
        row.append(InlineKeyboardButton(text, callback_data=callback))
        if len(row) >= row_width:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard():
    """Main menu keyboard"""
    buttons = [
        ("📡 القروبات", "menu_groups"),
        ("🔑 الكلمات المفتاحية", "menu_keywords"),
        ("📥 قروب الاستقبال", "menu_destination"),
        ("📊 الإحصائيات", "menu_stats"),
        ("⚙️ الإعدادات", "menu_settings"),
        ("📱 الحساب المراقب", "menu_userbot"),
        ("📋 سجل الطلبات", "menu_logs"),
        ("▶️ تشغيل", "bot_start")  # or ⏸ إيقاف
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
