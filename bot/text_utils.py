# -*- coding: utf-8 -*-
"""Arabic text messages for all bot screens"""

def start_text(name):
    return f"""مرحباً بك يا **{name}** 👋

أنا بوت **تجميع طلبات التوصيل**

أساعدك في مراقبة قروبات التوصيل تلقائياً وتحويل الطلبات المناسبة لك مباشرة

🔗 أضف روابط القروبات
🔑 حدد الكلمات المفتاحية
📥 واستقبل الطلبات تلقائياً

للبدء، اضغط الزر بالأسفل"""

def setup_account_text():
    return """⚙️ **إعداد الحساب المراقب**

لكي أتمكن من مراقبة القروبات، أحتاج ربط حساب تيليجرام يدخل هذه القروبات نيابةً عنك

📌 **الخطوات:**

1️⃣ أرسل لي رقم الهاتف المربوط بالحساب المراقب
2️⃣ سيصلك كود تحقق على تيليجرام
3️⃣ أرسل لي الكود هنا

⚠️ استخدم حساب مخصص للمراقبة فقط، لا تستخدم حسابك الشخصي"""

def enter_phone_text():
    return """📱 **أرسل رقم الهاتف الآن**

أرسل الرقم بالصيغة الدولية
مثال: +966512345678"""

def code_sent_text(phone):
    masked = phone[:7] + "XXXX" + phone[-2:]
    return f"""✅ تم إرسال كود التحقق إلى الرقم **{masked}**

🔢 أرسل لي الكود الآن"""

def account_linked_text(phone):
    masked = phone[:7] + "XXXX" + phone[-2:]
    return f"""✅ **تم ربط الحساب بنجاح!**

الحساب: **{masked}**
الحالة: 🟢 متصل

يمكنك الآن الانتقال للوحة التحكم"""

def main_menu_text(bot_status, userbot_status, groups_count, keywords_count, today_count, last_order_time):
    status_emoji = "🟢" if bot_status else "🔴"
    userbot_emoji = "🟢" if userbot_status else "🔴"
    return f"""🏠 **لوحة التحكم الرئيسية**

حالة البوت: {status_emoji} {"يعمل" if bot_status else "متوقف"}
حالة الحساب المراقب: {userbot_emoji} {"متصل" if userbot_status else "غير متصل"}
القروبات المراقبة: **{groups_count}** قروب
الكلمات المفتاحية: **{keywords_count}** كلمات
الطلبات اليوم: **{today_count}** طلب

آخر طلب مُحوّل: منذ **{last_order_time}**"""

def groups_menu_text(groups):
    active_count = sum(1 for g in groups if g.get("is_active", 1))
    text = f"""📡 **إدارة القروبات المراقبة**

القروبات النشطة حالياً: **{active_count}** قروب

"""
    for i, group in enumerate(groups, 1):
        status = "🟢" if group.get("is_active", 1) else "🟡"
        members = group.get("member_count", 0)
        text += f"{i}️⃣ {status} {group['title']} — {members:,} عضو\n"
    return text

def add_group_text():
    return """➕ **إضافة قروب جديد**

أرسل لي رابط القروب الآن

الصيغ المقبولة:
🔹 رابط عام: `https://t.me/group_name`
🔹 رابط خاص: `https://t.me/+AbCdEfGhIjK`
🔹 معرف القروب: `@group_name`

💡 يمكنك إرسال عدة روابط دفعة واحدة (كل رابط في سطر)"""

def group_added_text(title, members):
    return f"""✅ **تم إضافة القروب بنجاح!**

📌 الاسم: {title}
👥 الأعضاء: {members:,}
📊 الحالة: 🟢 نشط — بدأت المراقبة

سيتم تحويل أي رسالة تحتوي كلماتك المفتاحية تلقائياً"""

def group_add_failed_text():
    return """❌ **تعذر الانضمام للقروب**

السبب المحتمل:
🔸 الرابط منتهي الصلاحية
🔸 القروب يتطلب موافقة أدمن
🔸 الحساب المراقب محظور من هذا القروب

تأكد من صلاحية الرابط وأعد المحاولة"""

def delete_group_text(groups):
    text = "🗑 **حذف قروب من المراقبة**\n\nاختر القروب الذي تريد حذفه:\n\n"
    return text

def confirm_delete_group_text(title):
    return f"""⚠️ **تأكيد الحذف**

هل أنت متأكد من حذف:
📌 **{title}**

سيتم إيقاف المراقبة ومغادرة القروب نهائياً"""

def keywords_menu_text(keywords):
    text = """🔑 **إدارة الكلمات المفتاحية**

هذه الكلمات يبحث عنها البوت في رسائل القروبات
عند وجود أي كلمة منها، يتم تحويل الرسالة لك فوراً

الكلمات الحالية:

"""
    for i, word in enumerate(keywords, 1):
        text += f"{i}. `{word}`\n"
    text += f"\nالمجموع: **{len(keywords)}** كلمات مفتاحية"
    return text

def add_keyword_text():
    return """➕ **إضافة كلمة مفتاحية جديدة**

أرسل الكلمة أو العبارة التي تريد مراقبتها

💡 ملاحظات:
🔹 يمكنك إرسال عدة كلمات دفعة واحدة (كل كلمة في سطر)
🔹 البحث لا يفرق بين الحروف الكبيرة والصغيرة
🔹 يمكنك كتابة عبارة كاملة مثل: "أبحث عن مندوب""""

def keywords_added_text(words, total):
    text = "✅ تمت إضافة الكلمات التالية:\n\n"
    for word in words:
        text += f"🔹 `{word}`\n"
    text += f"\nالمجموع الكلي الآن: **{total}** كلمات مفتاحية"
    return text

def destination_group_text(title, username, status):
    status_emoji = "🟢" if status else "🔴"
    return f"""📥 **قروب الاستقبال**

هذا هو القروب الذي ستُحوّل إليه الطلبات المطابقة

القروب الحالي: **{title}**
المعرف: `{username}`
الحالة: {status_emoji} {"متصل" if status else "غير متصل"}"""

def change_destination_text():
    return """🔄 **تغيير قروب الاستقبال**

أرسل لي رابط أو معرف القروب الجديد

⚠️ شروط مهمة:
🔹 يجب أن يكون البوت عضو وأدمن في هذا القروب
🔹 يجب أن يملك صلاحية إرسال الرسائل

الصيغ المقبولة:
🔹 `https://t.me/group_name`
🔹 `@group_name`"""

def stats_text(today_checked, today_forwarded, week_checked, week_forwarded, 
               month_checked, month_forwarded, top_groups, top_keywords):
    text = f"""📊 **إحصائيات المراقبة**

📅 **إحصائيات اليوم:**
📨 الرسائل المراقبة: **{today_checked:,}**
✅ الطلبات المُحوّلة: **{today_forwarded:,}**

📅 **إحصائيات الأسبوع:**
📨 الرسائل المراقبة: **{week_checked:,}**
✅ الطلبات المُحوّلة: **{week_forwarded:,}**

📅 **إحصائيات الشهر:**
📨 الرسائل المراقبة: **{month_checked:,}**
✅ الطلبات المُحوّلة: **{month_forwarded:,}**

📡 **أكثر القروبات نشاطاً:**
"""
    for i, (name, count) in enumerate(top_groups, 1):
        text += f"{i}. {name} — {count} طلب\n"

    text += "\n🔑 **أكثر الكلمات تطابقاً:**\n"
    for i, (word, count) in enumerate(top_keywords, 1):
        text += f'{i}. "{word}" — {count} مرة\n'

    return text

def settings_text():
    return "⚙️ **إعدادات البوت**"

def blacklist_menu_text(words):
    text = """🚫 **الكلمات المستبعدة**

حتى لو احتوت الرسالة على كلمة مفتاحية، سيتم تجاهلها إذا احتوت على أي من هذه الكلمات

الكلمات المستبعدة حالياً:

"""
    for i, word in enumerate(words, 1):
        text += f"{i}. `{word}`\n"
    text += f"\nالمجموع: **{len(words)}** كلمات مستبعدة"
    return text

def message_format_preview_text(format_type):
    if format_type == "full":
        return """📝 **تنسيق الرسالة المُحوّلة**

**النموذج الحالي (الكامل):**

📥 **طلب جديد!**
📡 المصدر: قروب توصيل الرياض
🔑 الكلمة: "محتاج توصيل"
🕐 الوقت: 02:35 م
👤 المرسل: @username

💬 نص الرسالة:
"السلام عليكم، محتاج توصيل طرد من الرياض للدمام""""
    elif format_type == "short":
        return """📝 **تنسيق الرسالة المُحوّلة**

**النموذج المختصر:**

📥 طلب من: قروب توصيل الرياض
🔑 "محتاج توصيل"
👤 @username

💬 "السلام عليكم، محتاج توصيل طرد من الرياض للدمام""""
    else:
        return """📝 **تنسيق الرسالة المُحوّلة**

**التمرير المباشر:**

(يتم إعادة توجيه الرسالة كما هي بدون أي تنسيق إضافي)"""

def pause_confirm_text():
    return """⏸ **إيقاف مؤقت**

هل تريد إيقاف المراقبة مؤقتاً؟
الحساب سيبقى في القروبات لكن لن يتم تحويل أي رسائل"""

def paused_text(duration_minutes, resume_time):
    return f"""⏸ **تم الإيقاف المؤقت**

المراقبة متوقفة مؤقتاً
ستعود تلقائياً بعد: **{duration_minutes} دقيقة** ({resume_time})

أو يمكنك إعادة التشغيل يدوياً"""

def userbot_status_text(phone, status, last_activity, groups_count, uptime):
    status_emoji = "🟢" if status else "🔴"
    return f"""📱 **الحساب المراقب**

الرقم: **{phone}**
الحالة: {status_emoji} {"متصل" if status else "غير متصل"}
آخر نشاط: منذ **{last_activity}**
القروبات المنضم لها: **{groups_count}** قروب
وقت التشغيل: **{uptime}**"""

def logs_text(messages, total_today):
    text = f"""📋 **سجل آخر الطلبات المُحوّلة**

"""
    for i, msg in enumerate(messages, 1):
        time_str = msg.get("created_at", "غير معروف")
        group = msg.get("group_title", "غير معروف")
        keyword = msg.get("keyword", "غير معروف")
        content = msg.get("message_text", "")[:100]
        text += f"""{i}️⃣ 🕐 {time_str}
📡 {group}
🔑 "{keyword}"
💬 "{content}..."

"""
    text += f"عرض **{len(messages)}** من أصل **{total_today}** طلب اليوم"
    return text

def forwarded_message_text(order_num, group_title, sender, keyword, time_str, message_text):
    return f"""📥 **طلب جديد** #طلب_{order_num}

📡 **المصدر:** {group_title}
👤 **المرسل:** {sender}
🔑 **الكلمة المطابقة:** "{keyword}"
🕐 **الوقت:** {time_str}

💬 **نص الطلب:**
"{message_text}""""

def alert_disconnected_text(phone, last_activity):
    return f"""🔴 **تنبيه: الحساب المراقب انقطع!**

توقف الحساب **{phone}** عن الاستجابة
آخر نشاط: منذ **{last_activity}**

السبب المحتمل: انقطاع الإنترنت أو تسجيل خروج"""

def alert_removed_text(group_title):
    return f"""⚠️ **تنبيه: تم إزالة الحساب من قروب!**

تمت إزالة الحساب المراقب من:
📌 **{group_title}**

لن يتم مراقبة هذا القروب بعد الآن"""

def help_text():
    return """📖 **دليل استخدام البوت**

**الأوامر المتاحة:**
/start — بدء البوت
/menu — لوحة التحكم
/groups — القروبات
/addgroup — إضافة قروب
/keywords — الكلمات المفتاحية
/addword — إضافة كلمة
/stats — الإحصائيات
/pause — إيقاف مؤقت
/resume — استئناف
/status — الحالة
/logs — السجل
/settings — الإعدادات
/help — المساعدة

**كيف يعمل:**
1. اربط حساب تيليجرام للمراقبة
2. أضف قروبات التوصيل
3. حدد الكلمات المفتاحية
4. استقبل الطلبات تلقائياً!"""
