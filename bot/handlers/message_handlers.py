# -*- coding: utf-8 -*-
"""Message handlers for text input during conversations"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.state_manager import State
from bot.keyboard_utils import (
    main_menu_keyboard, groups_menu_keyboard, keywords_menu_keyboard,
    back_button, create_keyboard
)
from bot.text_utils import (
    code_sent_text, account_linked_text, group_added_text, group_add_failed_text,
    keywords_added_text, destination_group_text
)

logger = logging.getLogger(__name__)

class MessageHandlers:
    """Handle text messages based on user state"""

    @staticmethod
    def setup(application, db, state_manager, bot_manager):
        """Register message handlers"""
        handlers = MessageHandlers(db, state_manager, bot_manager)

        # Handle text messages
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text)
        )

    def __init__(self, db, state_manager, bot_manager):
        self.db = db
        self.state_manager = state_manager
        self.bot_manager = bot_manager

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main text message dispatcher"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        state = self.state_manager.get_state(user_id)

        if state.state == State.IDLE:
            # No active state - ignore or show help
            await update.message.reply_text(
                "استخدم /menu للوحة التحكم أو /help للمساعدة",
                reply_markup=main_menu_keyboard()
            )
            return

        elif state.state == State.WAITING_PHONE:
            await self._handle_phone(update, context, text)

        elif state.state == State.WAITING_CODE:
            await self._handle_code(update, context, text)

        elif state.state == State.WAITING_GROUP_LINK:
            await self._handle_group_link(update, context, text)

        elif state.state == State.WAITING_KEYWORD:
            await self._handle_keyword(update, context, text)

        elif state.state == State.WAITING_BLACKLIST:
            await self._handle_blacklist(update, context, text)

        elif state.state == State.WAITING_DESTINATION_GROUP:
            await self._handle_destination_group(update, context, text)

        elif state.state == State.WAITING_ADMIN_ADD:
            await self._handle_admin_add(update, context, text)

        else:
            await update.message.reply_text(
                "الأمر غير واضح. استخدم /menu للعودة للوحة التحكم.",
                reply_markup=main_menu_keyboard()
            )

    async def _handle_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle phone number input"""
        # Validate phone format
        phone_pattern = r'^\+[1-9]\d{7,15}$'
        if not re.match(phone_pattern, text):
            await update.message.reply_text(
                "❌ **رقم غير صحيح**\n\nأرسل الرقم بالصيغة الدولية\nمثال: +966512345678",
                reply_markup=back_button("back_start"),
                parse_mode="Markdown"
            )
            return

        # Store phone
        self.state_manager.set_data(update.effective_user.id, "phone", text)

        # Send code via userbot
        if self.bot_manager.userbot:
            try:
                await self.bot_manager.userbot.create_client(phone=text)
                result = await self.bot_manager.userbot.send_code(text)

                if result.get("status") == "code_sent":
                    self.state_manager.set_data(update.effective_user.id, "phone_code_hash", result.get("phone_code_hash"))
                    self.state_manager.set_state(update.effective_user.id, State.WAITING_CODE)

                    await update.message.reply_text(
                        code_sent_text(text),
                        reply_markup=back_button("back_start"),
                        parse_mode="Markdown"
                    )
                elif result.get("status") == "already_authorized":
                    # Already logged in
                    session_string = StringSession.save(self.bot_manager.userbot.client.session)
                    self.db.save_userbot_session(phone=text, session_string=session_string)
                    self.bot_manager.userbot_status = True
                    self.state_manager.clear_state(update.effective_user.id)

                    await update.message.reply_text(
                        account_linked_text(text),
                        reply_markup=create_keyboard([("🏠 لوحة التحكم", "menu")], row_width=1),
                        parse_mode="Markdown"
                    )

                    # Start monitoring
                    await self.bot_manager._connect_userbot()
                else:
                    await update.message.reply_text(
                        f"❌ **خطأ:** {result.get('error', 'Unknown error')}",
                        reply_markup=back_button("back_start"),
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Phone verification error: {e}")
                await update.message.reply_text(
                    f"❌ **خطأ في إرسال الكود:** {str(e)}\n\nتأكد من صحة API_ID و API_HASH",
                    reply_markup=back_button("back_start"),
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ **لم يتم إعداد UserBot**\n\nتحقق من إعدادات API_ID و API_HASH في ملف .env",
                reply_markup=back_button("back_start"),
                parse_mode="Markdown"
            )

    async def _handle_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle verification code input"""
        phone = self.state_manager.get_data(update.effective_user.id, "phone")

        if not phone:
            await update.message.reply_text(
                "❌ **خطأ: لم يتم العثور على الرقم**\n\nابدأ من جديد بـ /start",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return

        # Verify code
        if self.bot_manager.userbot:
            try:
                result = await self.bot_manager.userbot.verify_code(text)

                if result.get("status") == "connected":
                    # Save session
                    self.db.save_userbot_session(
                        phone=result["phone"],
                        session_string=result["session_string"]
                    )
                    self.bot_manager.userbot_status = True

                    # Clear state
                    self.state_manager.clear_state(update.effective_user.id)

                    await update.message.reply_text(
                        account_linked_text(phone),
                        reply_markup=create_keyboard([("🏠 لوحة التحكم", "menu")], row_width=1),
                        parse_mode="Markdown"
                    )

                    # Start monitoring
                    await self.bot_manager._connect_userbot()
                else:
                    await update.message.reply_text(
                        f"❌ **خطأ في التحقق:** {result.get('error', 'Unknown error')}",
                        reply_markup=back_button("back_start"),
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Code verification error: {e}")
                await update.message.reply_text(
                    f"❌ **خطأ:** {str(e)}\n\nأعد إرسال الكود أو ابدأ من جديد بـ /start",
                    reply_markup=back_button("back_start"),
                    parse_mode="Markdown"
                )

    async def _handle_group_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle group link input"""
        links = [line.strip() for line in text.split("\n") if line.strip()]

        added_groups = []
        failed_groups = []

        for link in links:
            # Extract group info from link
            group_info = self._parse_group_link(link)

            if not group_info:
                failed_groups.append((link, "رابط غير صحيح"))
                continue

            # Try to join via userbot
            if self.bot_manager.userbot and self.bot_manager.userbot.is_connected:
                try:
                    result = await self.bot_manager.userbot.join_group(link)
                    if result.get("success"):
                        # Save to database
                        self.db.add_group(
                            chat_id=result["chat_id"],
                            title=result["title"],
                            username=result.get("username"),
                            invite_link=link,
                            member_count=result.get("member_count", 0),
                            is_private="/+" in link or "joinchat/" in link
                        )
                        added_groups.append(result["title"])

                        # Restart monitoring with new group
                        groups = self.db.get_groups(active_only=True)
                        await self.bot_manager.userbot.start_monitoring(groups)
                    else:
                        failed_groups.append((link, result.get("error", "Unknown error")))
                except Exception as e:
                    logger.error(f"Join group error: {e}")
                    failed_groups.append((link, str(e)))
            else:
                # UserBot not connected - save manually for later
                self.db.add_group(
                    chat_id=group_info.get("chat_id", 0),
                    title=group_info.get("title", link),
                    username=group_info.get("username"),
                    invite_link=link,
                    is_private="/+" in link or "joinchat/" in link
                )
                added_groups.append(group_info.get("title", link))

        # Send results
        if added_groups:
            text = f"✅ **تم إضافة {len(added_groups)} قروب**\n\n"
            for name in added_groups:
                text += f"📌 {name}\n"
        else:
            text = ""

        if failed_groups:
            text += f"\n❌ **فشل في {len(failed_groups)} قروب**\n\n"
            for link, error in failed_groups:
                text += f"🔗 {link}\n⚠️ {error}\n\n"

        keyboard = create_keyboard([
            ("➕ إضافة قروب آخر", "add_group"),
            ("📡 القروبات", "menu_groups"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.clear_state(update.effective_user.id)

    def _parse_group_link(self, link: str) -> dict:
        """Parse group link to extract info"""
        link = link.strip()

        if link.startswith("@"):
            return {"username": link[1:], "title": link, "chat_id": 0}

        if "t.me/" in link or "telegram.me/" in link:
            parts = link.split("/")
            last_part = parts[-1] if parts else ""

            if last_part.startswith("+"):
                return {"invite_link": link, "title": "قروب خاص", "chat_id": 0, "is_private": True}
            elif "joinchat" in last_part:
                return {"invite_link": link, "title": "قروب خاص", "chat_id": 0, "is_private": True}
            else:
                return {"username": last_part, "title": last_part, "chat_id": 0, "is_private": False}

        return None

    async def _handle_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle keyword input"""
        words = [line.strip() for line in text.split("\n") if line.strip()]

        # Check if replacing
        state = self.state_manager.get_state(update.effective_user.id)
        if state.data.get("replace"):
            self.db.clear_keywords()

        added = []
        for word in words:
            if self.db.add_keyword(word):
                added.append(word)

        total = len(self.db.get_keywords())

        if added:
            text = keywords_added_text(added, total)
        else:
            text = f"⚠️ **لم تُضف كلمات جديدة** (قد تكون موجودة بالفعل)\n\nالمجموع الكلي: **{total}** كلمات"

        keyboard = create_keyboard([
            ("➕ إضافة المزيد", "add_keyword"),
            ("🔑 الكلمات المفتاحية", "menu_keywords"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.clear_state(update.effective_user.id)

    async def _handle_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle blacklist word input"""
        words = [line.strip() for line in text.split("\n") if line.strip()]

        added = []
        for word in words:
            if self.db.add_blacklist(word):
                added.append(word)

        total = len(self.db.get_blacklist())

        if added:
            text = f"✅ **تمت إضافة الكلمات المستبعدة:**\n\n"
            for word in added:
                text += f"🔹 `{word}`\n"
            text += f"\nالمجموع: **{total}** كلمات مستبعدة"
        else:
            text = f"⚠️ **لم تُضف كلمات جديدة**\n\nالمجموع: **{total}** كلمات مستبعدة"

        keyboard = create_keyboard([
            ("➕ إضافة المزيد", "add_blacklist"),
            ("⚙️ الإعدادات", "menu_settings"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.clear_state(update.effective_user.id)

    async def _handle_destination_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle destination group input"""
        # Parse group link/username
        group_info = self._parse_group_link(text)

        if not group_info:
            await update.message.reply_text(
                "❌ **رابط غير صحيح**\n\nأرسل رابط صحيح أو معرف القروب",
                reply_markup=back_button("menu_destination"),
                parse_mode="Markdown"
            )
            return

        # Try to verify the group by sending a test message
        try:
            # For username-based groups, try to resolve
            chat_id = None
            if group_info.get("username"):
                try:
                    chat = await context.bot.get_chat(f"@{group_info['username']}")
                    chat_id = chat.id
                    group_info["title"] = chat.title or group_info["username"]
                except Exception as e:
                    logger.warning(f"Could not resolve chat: {e}")
                    chat_id = text  # Use raw text as fallback
            else:
                chat_id = text

            # Save settings
            self.db.set_setting("destination_group_id", str(chat_id))
            self.db.set_setting("destination_group_title", group_info.get("title", "قروب الاستقبال"))
            self.db.set_setting("destination_group_username", group_info.get("username", text))

            text = destination_group_text(
                group_info.get("title", "قروب الاستقبال"),
                group_info.get("username", text),
                True
            )

            keyboard = create_keyboard([
                ("🧪 رسالة تجريبية", "test_destination"),
                ("📥 قروب الاستقبال", "menu_destination"),
                ("◀️ رجوع", "back_main")
            ], row_width=2)

            await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
            self.state_manager.clear_state(update.effective_user.id)

        except Exception as e:
            logger.error(f"Destination group error: {e}")
            await update.message.reply_text(
                f"❌ **خطأ:** {str(e)}\n\nتأكد من أن البوت عضو في القروب",
                reply_markup=back_button("menu_destination"),
                parse_mode="Markdown"
            )

    async def _handle_admin_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle admin addition"""
        # Parse username or user_id
        username = text.replace("@", "").strip()

        try:
            # Try to get user info from Telegram
            # First try as user_id
            try:
                user_id = int(username)
            except ValueError:
                user_id = 0

            if user_id > 0:
                try:
                    chat = await context.bot.get_chat(user_id)
                    actual_username = chat.username or username
                    actual_id = chat.id
                except:
                    actual_username = username
                    actual_id = 0
            else:
                actual_username = username
                actual_id = 0

            self.db.add_admin(
                user_id=actual_id,
                username=actual_username,
                added_by=update.effective_user.id
            )

            text = f"✅ **تمت إضافة المشرف:** @{actual_username}\n\n"
            if actual_id == 0:
                text += "⚠️ سيتم تحديث المعرف عند أول تفاعل للمستخدم مع البوت."

        except Exception as e:
            text = f"❌ **خطأ:** {str(e)}"

        keyboard = create_keyboard([
            ("➕ إضافة مشرف", "add_admin"),
            ("👤 المشرفين", "settings_admins"),
            ("◀️ رجوع", "back_main")
        ], row_width=2)

        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
        self.state_manager.clear_state(update.effective_user.id)

from telethon.sessions import StringSession
