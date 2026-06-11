# بوت تجميع طلبات التوصيل | Delivery Order Aggregator Bot

بوت تيليجرام ذكي لمراقبة قروبات التوصيل تلقائياً وتحويل الطلبات المناسبة لك.

## المميزات

- ✅ مراقبة تلقائية لقروبات التوصيل
- ✅ تصفية بالكلمات المفتاحية
- ✅ تحويل فوري للطلبات إلى قروبك الخاص
- ✅ إحصائيات تفصيلية
- ✅ قائمة سوداء للكلمات المستبعدة
- ✅ منع تكرار الرسائل
- ✅ إدارة المشرفين
- ✅ إيقاف مؤقت بمدد محددة

## المتطلبات

- Python 3.8+
- حساب تيليجرام للمراقبة (UserBot)
- توكن بوت من @BotFather
- API_ID و API_HASH من my.telegram.org

## التثبيت

```bash
# 1. نسخ المشروع
cd delivery_bot

# 2. إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. إعداد المتغيرات
# أنسخ .env.example إلى .env واملأ البيانات
cp .env.example .env
# عدل الملف بمحرر النصوص

# 5. تشغيل البوت
python main.py
```

## الإعداد

### 1. الحصول على API_ID و API_HASH

1. اذهب إلى https://my.telegram.org
2. سجل دخول بحساب تيليجرام
3. اذهب إلى "API development tools"
4. أنشئ تطبيق جديد
5. احفظ API_ID و API_HASH

### 2. الحصول على Bot Token

1. افتح @BotFather في تيليجرام
2. أرسل `/newbot`
3. اتبع التعليمات واحفظ التوكن

### 3. تشغيل البوت لأول مرة

1. شغل البوت: `python main.py`
2. افتح البوت في تيليجرام واضغط `/start`
3. أرسل رقم الهاتف للحساب المراقب
4. أدخل كود التحقق
5. أضف قروبات التوصيل
6. حدد الكلمات المفتاحية
7. استقبل الطلبات! 🎉

## الأوامر

| الأمر | الوظيفة |
|-------|---------|
| `/start` | بدء البوت |
| `/menu` | لوحة التحكم |
| `/groups` | القروبات |
| `/addgroup` | إضافة قروب |
| `/keywords` | الكلمات المفتاحية |
| `/addword` | إضافة كلمة |
| `/stats` | الإحصائيات |
| `/pause` | إيقاف مؤقت |
| `/resume` | استئناف |
| `/status` | الحالة |
| `/logs` | السجل |
| `/settings` | الإعدادات |
| `/help` | المساعدة |

## هيكل المشروع

```
delivery_bot/
├── main.py                      # نقطة الدخول
├── requirements.txt             # المكتبات المطلوبة
├── .env.example                 # نموذج الإعدادات
├── README.md                    # هذا الملف
├── bot/
│   ├── __init__.py
│   ├── config.py                # الإعدادات
│   ├── database.py              # قاعدة البيانات
│   ├── state_manager.py         # إدارة الحالات
│   ├── bot_manager.py           # المدير الرئيسي
│   ├── userbot_manager.py       # إدارة UserBot
│   ├── keyboard_utils.py        # لوحات المفاتيح
│   ├── text_utils.py            # النصوص العربية
│   └── handlers/
│       ├── __init__.py
│       ├── command_handlers.py  # معالجات الأوامر
│       ├── callback_handlers.py # معالجات الأزرار
│       └── message_handlers.py  # معالجات الرسائل
└── data/
    └── bot.db                   # قاعدة البيانات SQLite
```

## ملاحظات هامة

⚠️ **استخدم حساب تيليجرام مخصص للمراقبة فقط** — لا تستخدم حسابك الشخصي

⚠️ **تأكد من أن البوت عضو وأدمن في قروب الاستقبال**

⚠️ **لا تُشارك API_ID و API_HASH مع أحد**

## الترخيص

MIT License
