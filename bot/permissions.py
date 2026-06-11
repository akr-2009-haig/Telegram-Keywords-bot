# -*- coding: utf-8 -*-
"""Permission system for bot access control"""

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

class Permission:
    """Permission constants"""
    ALL = "all"
    VIEW_GROUPS = "view_groups"
    MANAGE_GROUPS = "manage_groups"
    VIEW_KEYWORDS = "view_keywords"
    MANAGE_KEYWORDS = "manage_keywords"
    VIEW_STATS = "view_stats"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_ADMINS = "manage_admins"
    PAUSE_BOT = "pause_bot"
    VIEW_LOGS = "view_logs"

class PermissionChecker:
    """Check permissions for users"""

    def __init__(self, db):
        self.db = db

    def check(self, user_id: int, permission: str) -> bool:
        """Check if user has permission"""
        return self.db.has_permission(user_id, permission)

    def require(self, permission: str):
        """Decorator to require permission"""
        def decorator(func):
            @wraps(func)
            async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
                user_id = update.effective_user.id
                if not self.check(user_id, permission):
                    await update.effective_message.reply_text(
                        "⛔ **ليس لديك صلاحية للقيام بهذا الإجراء**\n\n"
                        "تواصل مع المالك للحصول على الصلاحيات.",
                        parse_mode="Markdown"
                    )
                    return
                return await func(update, context, *args, **kwargs)
            return wrapper
        return decorator

# Default permissions for new admins
DEFAULT_ADMIN_PERMISSIONS = [
    Permission.VIEW_GROUPS,
    Permission.VIEW_KEYWORDS,
    Permission.VIEW_STATS,
    Permission.VIEW_LOGS,
    Permission.PAUSE_BOT
]

# Full permissions for managers
MANAGER_PERMISSIONS = [
    Permission.ALL
]
