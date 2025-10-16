"""
Localized user-facing messages for the bot.

FIXED VERSION:
- Added file operations messages
- All messages are plain text (no Markdown)
"""

from models_enums import Language

# ============================================================================
# MESSAGE DICTIONARY
# ============================================================================

_MESSAGES = {
    # ========================================================================
    # WELCOME & NAVIGATION
    # ========================================================================
    "welcome": {
        Language.en: "👋 Welcome! I'm your AI assistant bot. Please choose your language.",
        Language.ru: "👋 Добро пожаловать! Я ваш AI-ассистент. Пожалуйста, выберите язык.",
        Language.uz: "👋 Xush kelibsiz! Men sizning AI yordamchingizman. Iltimos, tilni tanlang.",
    },

    "prompt_main_menu": {
        Language.en: "Choose an option from the menu below:",
        Language.ru: "Выберите опцию из меню ниже:",
        Language.uz: "Quyidagi menyudan birini tanlang:",
    },

    "prompt_ai_menu": {
        Language.en: "Select an AI function:",
        Language.ru: "Выберите AI функцию:",
        Language.uz: "AI funksiyani tanlang:",
    },

    # 🆕 NEW: File operations menu
    "prompt_file_menu": {
        Language.en: "📁 File Operations\n\nSelect an operation:",
        Language.ru: "📁 Работа с файлами\n\nВыберите операцию:",
        Language.uz: "📁 Fayllar bilan ishlash\n\nOperatsiyani tanlang:",
    },

    # ========================================================================
    # FEATURE ENTRY MESSAGES
    # ========================================================================
    "enter_chat": {
        Language.en: "💬 Chat Mode Activated!\n\nSend me any message and I'll respond. I can help with:\n• Questions and explanations\n• Code writing and debugging\n• Creative writing\n• General conversation\n\nCommands:\n/clear - Clear chat history\n\nPress BACK when finished.",
        Language.ru: "💬 Режим чата активирован!\n\nОтправьте мне любое сообщение, и я отвечу. Я могу помочь с:\n• Вопросами и объяснениями\n• Написанием и отладкой кода\n• Творческим письмом\n• Общением\n\nКоманды:\n/clear - Очистить историю\n\nНажмите НАЗАД, когда закончите.",
        Language.uz: "💬 Suhbat rejimi faollashtirildi!\n\nMenga xabar yuboring va men javob beraman. Men yordam bera olaman:\n• Savollar va tushuntirishlar\n• Kod yozish va tuzatish\n• Ijodiy yozish\n• Umumiy suhbat\n\nBuyruqlar:\n/clear - Tarixni tozalash\n\nORQAGA tugmasini bosing, tugagach.",
    },

    "enter_image_edit": {
        Language.en: """🛠 **Smart Image Editing Mode**

How it works:
1️⃣ Send ONE image
2️⃣ Describe what to change

**AI will:**
✨ Analyze your photo with advanced vision
🎨 Maintain your pose and composition  
🖼️ Apply edits naturally and realistically

**Example requests:**
• "Make sky blue and add neon eyebrows"
• "Change background to beach sunset"
• "Add sunglasses, make it nighttime"
• "Turn into Van Gogh painting style"

**Tips for best results:**
✅ Be specific and clear
✅ Describe colors, objects, style
❌ Avoid vague requests

**Premium Feature:**
• 3 free edits per week
• Unlimited for premium

Press BACK when finished.""",

        Language.ru: """🛠 **Умное редактирование изображений**

Как работает:
1️⃣ Отправьте ОДНО изображение
2️⃣ Опишите что изменить

**AI сделает:**
✨ Проанализирует фото продвинутым зрением
🎨 Сохранит вашу позу и композицию
🖼️ Применит правки естественно и реалистично

**Примеры запросов:**
• "Сделай небо синим и добавь неоновые брови"
• "Смени фон на закат на пляже"
• "Добавь очки, сделай ночь"
• "Преврати в стиль Ван Гога"

**Советы для лучших результатов:**
✅ Будьте конкретны и ясны
✅ Описывайте цвета, объекты, стиль
❌ Избегайте размытых запросов

**Премиум функция:**
• 3 бесплатных редактирования в неделю
• Безлимит для премиум

Нажмите НАЗАД когда закончите.""",

        Language.uz: """🛠 **Aqlli rasm tahrirlash rejimi**

Qanday ishlaydi:
1️⃣ BITTA rasm yuboring
2️⃣ Nima o'zgartirishni tasvirlab bering

**AI qiladi:**
✨ Fotoingizni ilg'or ko'rish bilan tahlil qiladi
🎨 Pozangiz va kompozitsiyangizni saqlaydi
🖼️ Tahrirlashlarni tabiiy va real qo'llaydi

**So'rov misollari:**
• "Osmonni ko'k qiling va neon qoshlar qo'shing"
• "Fonni plyaj quyosh botishiga o'zgartiring"
• "Ko'zoynak qo'shing, kechaga aylantiring"
• "Van Gog uslubiga aylantiring"

**Eng yaxshi natija uchun:**
✅ Aniq va ravshan bo'ling
✅ Ranglar, narsalar, uslubni tasvirlab bering
❌ Noaniq so'rovlardan saqlaning

**Premium funksiya:**
• Haftada 3 ta bepul tahrirlash
• Premium uchun cheklovsiz

Tugagach ORQAGA bosing.""",
    },

    "enter_image_gen": {
        Language.en: "🎨 Image Generation Mode\n\nDescribe the image you want to create in detail.\n\nExamples:\n• \"Futuristic city skyline at sunset\"\n• \"Cute robot playing guitar in space\"\n• \"Abstract art with blue and gold colors\"\n\n✨ This is a premium feature with free trial available!",
        Language.ru: "🎨 Режим генерации изображений\n\nПодробно опишите изображение, которое хотите создать.\n\nПримеры:\n• «Футуристический городской пейзаж на закате»\n• «Милый робот играет на гитаре в космосе»\n• «Абстрактное искусство синего и золотого цвета»\n\n✨ Это премиум-функция с бесплатной пробной версией!",
        Language.uz: "🎨 Rasm yaratish rejimi\n\nYaratmoqchi bo'lgan rasmingizni batafsil tasvirlab bering.\n\nMisollar:\n• \"Kelajak shahrining quyosh botishidagi manzarasi\"\n• \"Kosmosda gitara chalayotgan yoqimli robot\"\n• \"Ko'k va oltin rangdagi abstrakt san'at\"\n\n✨ Bu premium funksiya, bepul sinov mavjud!",
    },

    "enter_pptx": {
        Language.en: "📊 Presentation Creator\n\nStep 1: Choose a theme (1-4)\nStep 2: Describe your topic in detail\n\nI'll create a professional presentation with:\n• 10-12 comprehensive slides\n• Professional design\n• Detailed content with examples\n• Key points and statistics\n\n✨ This is a premium feature with free trial available!",
        Language.ru: "📊 Создатель презентаций\n\nШаг 1: Выберите тему (1-4)\nШаг 2: Подробно опишите вашу тему\n\nЯ создам профессиональную презентацию с:\n• 10-12 подробными слайдами\n• Профессиональным дизайном\n• Детальным контентом с примерами\n• Ключевыми моментами и статистикой\n\n✨ Это премиум-функция с бесплатной пробной версией!",
        Language.uz: "📊 Taqdimot yaratuvchi\n\n1-qadam: Mavzuni tanlang (1-4)\n2-qadam: Mavzungizni batafsil tasvirlab bering\n\nMen professional taqdimot yarataman:\n• 10-12 to'liq slayd\n• Professional dizayn\n• Misollar bilan batafsil kontent\n• Asosiy fikrlar va statistika\n\n✨ Bu premium funksiya, bepul sinov mavjud!",
    },

    "pptx_enter_topic": {
        Language.en: "📝 Great! Now describe your presentation topic in detail.\n\nFor best results, include:\n• Main subject\n• Target audience\n• Key points to cover\n• Any specific requirements\n\nExample: \"AI in Healthcare - Benefits, challenges, current applications, and future trends for medical professionals\"",
        Language.ru: "📝 Отлично! Теперь подробно опишите тему вашей презентации.\n\nДля лучшего результата включите:\n• Основную тему\n• Целевую аудиторию\n• Ключевые моменты\n• Специальные требования\n\nПример: «AI в здравоохранении - Преимущества, вызовы, текущие применения и будущие тренды для медицинских работников»",
        Language.uz: "📝 Ajoyib! Endi taqdimot mavzungizni batafsil tasvirlab bering.\n\nEng yaxshi natija uchun qo'shing:\n• Asosiy mavzu\n• Maqsadli auditoriya\n• Asosiy fikrlar\n• Maxsus talablar\n\nMisol: \"Sog'liqni saqlashda AI - Afzalliklar, qiyinchiliklar, hozirgi qo'llanmalar va tibbiyot mutaxassislari uchun kelajak tendensiyalari\"",
    },

    # 🆕 NEW: File operations messages
    "enter_doc_to_pdf": {
        Language.en: "📄 DOC → PDF Converter\n\nSend me a DOC or DOCX file and I'll convert it to PDF.",
        Language.ru: "📄 Конвертер DOC → PDF\n\nОтправьте мне файл DOC или DOCX, и я конвертирую его в PDF.",
        Language.uz: "📄 DOC → PDF konvertor\n\nMenga DOC yoki DOCX fayl yuboring, men uni PDF ga aylantirib beraman.",
    },

    "enter_txt_to_pdf": {
        Language.en: "📝 TXT → PDF Converter\n\nSend me a TXT file and I'll convert it to a formatted PDF.",
        Language.ru: "📝 Конвертер TXT → PDF\n\nОтправьте мне TXT файл, и я конвертирую его в форматированный PDF.",
        Language.uz: "📝 TXT → PDF konvertor\n\nMenga TXT fayl yuboring, men uni formatlangan PDF ga aylantirib beraman.",
    },

    "enter_rename_file": {
        Language.en: "✏️ File Renamer\n\nStep 1: Send any file\nStep 2: Send the new name\n\nI'll rename and send it back to you.",
        Language.ru: "✏️ Переименование файла\n\nШаг 1: Отправьте любой файл\nШаг 2: Отправьте новое имя\n\nЯ переименую и отправлю обратно.",
        Language.uz: "✏️ Fayl nomini o'zgartirish\n\n1-qadam: Istalgan fayl yuboring\n2-qadam: Yangi nom yuboring\n\nMen o'zgartirib qaytarib beraman.",
    },

    "enter_manual_pptx": {
        Language.en: "📊 Manual PPTX Creator\n\nSend me slide content in this format:\n\n---\nSlide 1 Title\nBullet point 1\nBullet point 2\n---\nSlide 2 Title\nBullet point 1\n---\n\nEach slide separated by ---",
        Language.ru: "📊 Ручное создание PPTX\n\nОтправьте контент слайдов в формате:\n\n---\nЗаголовок слайда 1\nПункт 1\nПункт 2\n---\nЗаголовок слайда 2\nПункт 1\n---\n\nКаждый слайд разделён ---",
        Language.uz: "📊 Qo'lda PPTX yaratish\n\nSlayd kontentini shu formatda yuboring:\n\n---\n1-slayd sarlavhasi\nBand 1\nBand 2\n---\n2-slayd sarlavhasi\nBand 1\n---\n\nHar bir slayd --- bilan ajratilgan",
    },

    "enter_merge_pdf": {
        Language.en: "🔗 PDF Merger\n\nSend me 2 or more PDF files (one by one), then send /merge to combine them.",
        Language.ru: "🔗 Объединение PDF\n\nОтправьте мне 2 или более PDF файла (по одному), затем отправьте /merge для объединения.",
        Language.uz: "🔗 PDF birlashtirish\n\nMenga 2 yoki undan ko'p PDF fayl yuboring (birma-bir), keyin /merge yuboring.",
    },

    "enter_ocr": {
        Language.en: "🔍 OCR - Extract Text from Image\n\nSend me an image with text and I'll extract the text for you.\n\nWorks best with:\n• Clear, high-resolution images\n• Good lighting\n• Printed text",
        Language.ru: "🔍 OCR - Извлечение текста из изображения\n\nОтправьте мне изображение с текстом, и я извлеку текст.\n\nЛучше всего работает с:\n• Чёткими изображениями высокого разрешения\n• Хорошим освещением\n• Печатным текстом",
        Language.uz: "🔍 OCR - Rasmdan matn ajratib olish\n\nMenga matnli rasm yuboring, men matnni ajratib beraman.\n\nEng yaxshi ishlaydi:\n• Aniq, yuqori sifatli rasmlar\n• Yaxshi yoritilgan\n• Chop etilgan matn",
    },

    # ========================================================================
    # PREMIUM & TRIAL MESSAGES (🔧 FIXED: Using config values)
    # ========================================================================
    "premium_required": {
        Language.en: "🔒 Premium Feature!\n\n✨ Upgrade to Premium to unlock:\n\n🎨 Image Generation - Create stunning AI images\n🛠 Image Editing - Transform your photos\n📊 PPTX Creation - Generate presentations\n🤖 Better AI Quality - GPT-4 access\n📈 Higher Daily Limits - Unlimited usage\n📁 Advanced File Operations\n\n💎 Contact @O_Mirzabek to upgrade!",
        Language.ru: "🔒 Премиум функция!\n\n✨ Обновитесь до Премиум, чтобы получить:\n\n🎨 Генерацию изображений - Создавайте потрясающие AI-изображения\n🛠 Редактирование изображений - Преобразуйте свои фото\n📊 Создание PPTX - Генерируйте презентации\n🤖 Лучшее качество AI - Доступ к GPT-4\n📈 Более высокие лимиты - Безлимитное использование\n📁 Продвинутые операции с файлами\n\n💎 Свяжитесь с @O_Mirzabek для апгрейда!",
        Language.uz: "🔒 Premium funksiya!\n\n✨ Premium'ga yangilang va oling:\n\n🎨 Rasm yaratish - Ajoyib AI rasmlar yarating\n🛠 Rasmni tahrirlash - Fotoingizni o'zgartiring\n📊 PPTX yaratish - Taqdimotlar yarating\n🤖 Yaxshiroq AI sifat - GPT-4 kirish\n📈 Yuqori limitlar - Cheklovsiz foydalanish\n📁 Ilg'or fayl operatsiyalari\n\n💎 Yangilash uchun @O_Mirzabek ga murojaat qiling!",
    },

    "quota_exceeded": {
        Language.en: "🚫 Daily Limit Reached!\n\nYou've used all your free requests for today.\n\n💎 Upgrade to Premium for unlimited access!\n\nContact @O_Mirzabek",
        Language.ru: "🚫 Дневной лимит исчерпан!\n\nВы использовали все бесплатные запросы на сегодня.\n\n💎 Обновитесь до Премиум для безлимитного доступа!\n\nСвяжитесь с @O_Mirzabek",
        Language.uz: "🚫 Kunlik limit tugadi!\n\nSiz bugungi barcha bepul so'rovlaringizni ishlatdingiz.\n\n💎 Cheklovsiz kirish uchun Premium'ga yangilang!\n\n@O_Mirzabek ga murojaat qiling",
    },

    "error_ai": {
        Language.en: "⚠️ AI service error. Please try again in a moment.",
        Language.ru: "⚠️ Ошибка AI сервиса. Попробуйте снова через момент.",
        Language.uz: "⚠️ AI xizmati xatosi. Bir ozdan keyin qayta urinib ko'ring.",
    },

    # ========================================================================
    # TRIAL SYSTEM MESSAGES
    # ========================================================================
    "trial_started": {
        Language.en: "🎁 Free Trial Started!\n\n✨ {feature} trial activated!\n\n📊 You have {remaining}/{total} uses\n⏰ Valid for {days} days\n\nEnjoy exploring premium features!",
        Language.ru: "🎁 Пробная версия запущена!\n\n✨ Пробная версия {feature} активирована!\n\n📊 У вас {remaining}/{total} использований\n⏰ Действует {days} дней\n\nНаслаждайтесь премиум-функциями!",
        Language.uz: "🎁 Bepul sinov boshlandi!\n\n✨ {feature} sinovi faollashtirildi!\n\n📊 Sizda {remaining}/{total} ta urinish\n⏰ {days} kun amal qiladi\n\nPremium funksiyalardan bahramand bo'ling!",
    },

    "trial_remaining": {
        Language.en: "🧪 Trial Usage\n\n📊 {feature}: {remaining}/{total} uses left",
        Language.ru: "🧪 Использование триала\n\n📊 {feature}: осталось {remaining}/{total}",
        Language.uz: "🧪 Sinov foydalanish\n\n📊 {feature}: {remaining}/{total} ta qoldi",
    },

    "trial_consumed": {
        Language.en: "✅ Trial Used\n\n📊 {feature}: {remaining}/{total} uses remaining",
        Language.ru: "✅ Триал использован\n\n📊 {feature}: осталось {remaining}/{total}",
        Language.uz: "✅ Sinov ishlatildi\n\n📊 {feature}: {remaining}/{total} ta qoldi",
    },

    "trial_over": {
        Language.en: "⛔ Trial Ended\n\nYour free trial for {feature} has ended.\n\n💎 Upgrade to Premium for unlimited access!\n\nContact @O_Mirzabek",
        Language.ru: "⛔ Триал закончился\n\nВаш бесплатный триал для {feature} закончился.\n\n💎 Обновитесь до Премиум для безлимитного доступа!\n\nСвяжитесь с @O_Mirzabek",
        Language.uz: "⛔ Sinov tugadi\n\n{feature} uchun bepul sinovingiz tugadi.\n\n💎 Cheklovsiz kirish uchun Premium'ga yangilang!\n\n@O_Mirzabek ga murojaat qiling",
    },

    "trial_renewed": {
        Language.en: "🔔 Trial Renewed!\n\n✨ Your {feature} trial has reset!\n\n📊 You now have {total} new uses for the next {days} days\n\nEnjoy!",
        Language.ru: "🔔 Триал обновлён!\n\n✨ Ваш триал {feature} обновился!\n\n📊 У вас теперь {total} новых использований на следующие {days} дней\n\nНаслаждайтесь!",
        Language.uz: "🔔 Sinov yangilandi!\n\n✨ {feature} sinovingiz yangilandi!\n\n📊 Endi sizda keyingi {days} kun uchun {total} ta yangi urinish bor\n\nBahramand bo'ling!",
    },

    # ========================================================================
    # PROFILE MESSAGES
    # ========================================================================
    "profile_info": {
        Language.en: "👤 Your Profile\n\n📋 Plan: {plan}\n💎 Premium: {premium}\n\n📊 Today's Usage:\n  • Chats: {chats}/{chat_limit}\n  • Conversions: {converts}/{convert_limit}\n  • PPTX: {pptx}/{pptx_limit}",
        Language.ru: "👤 Ваш профиль\n\n📋 План: {plan}\n💎 Премиум: {premium}\n\n📊 Использовано сегодня:\n  • Чаты: {chats}/{chat_limit}\n  • Конверсии: {converts}/{convert_limit}\n  • PPTX: {pptx}/{pptx_limit}",
        Language.uz: "👤 Sizning profilingiz\n\n📋 Reja: {plan}\n💎 Premium: {premium}\n\n📊 Bugungi foydalanish:\n  • Suhbatlar: {chats}/{chat_limit}\n  • Konversiyalar: {converts}/{convert_limit}\n  • PPTX: {pptx}/{pptx_limit}",
    },

    "language_changed": {
        Language.en: "✅ Language changed to English!",
        Language.ru: "✅ Язык изменен на русский!",
        Language.uz: "✅ Til o'zbek tiliga o'zgartirildi!",
    },

    "phone_added": {
        Language.en: "✅ Phone number saved successfully!",
        Language.ru: "✅ Номер телефона успешно сохранён!",
        Language.uz: "✅ Telefon raqami muvaffaqiyatli saqlandi!",
    },

    "phone_request": {
        Language.en: "📱 Please use the button below to share your phone number:",
        Language.ru: "📱 Пожалуйста, используйте кнопку ниже, чтобы отправить номер:",
        Language.uz: "📱 Telefon raqamingizni yuborish uchun quyidagi tugmani bosing:",
    },

    # ========================================================================
    # ADMIN MESSAGES
    # ========================================================================
    "admin_access_denied": {
        Language.en: "🚫 You don't have permission to use admin commands.",
        Language.ru: "🚫 У вас нет доступа к админ-командам.",
        Language.uz: "🚫 Sizda admin buyruqlaridan foydalanish huquqi yo'q.",
    },

    "admin_welcome": {
        Language.en: "⚙️ Admin Panel\n\nWelcome to the admin control panel.",
        Language.ru: "⚙️ Панель администратора\n\nДобро пожаловать в панель управления.",
        Language.uz: "⚙️ Admin paneli\n\nBoshqaruv paneliga xush kelibsiz.",
    },

    # ========================================================================
    # GENERAL MESSAGES
    # ========================================================================
    "cancelled": {
        Language.en: "❌ Operation cancelled.",
        Language.ru: "❌ Операция отменена.",
        Language.uz: "❌ Amal bekor qilindi.",
    },

    "back_to_menu": {
        Language.en: "⬅️ Returning to main menu...",
        Language.ru: "⬅️ Возврат в главное меню...",
        Language.uz: "⬅️ Asosiy menyuga qaytish...",
    },

    "processing": {
        Language.en: "⏳ Processing...",
        Language.ru: "⏳ Обработка...",
        Language.uz: "⏳ Qayta ishlanmoqda...",
    },

    "success": {
        Language.en: "✅ Success!",
        Language.ru: "✅ Успешно!",
        Language.uz: "✅ Muvaffaqiyatli!",
    },

    "error_general": {
        Language.en: "❌ An error occurred. Please try again.",
        Language.ru: "❌ Произошла ошибка. Попробуйте снова.",
        Language.uz: "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
    },

    "invalid_input": {
        Language.en: "⚠️ Invalid input. Please try again.",
        Language.ru: "⚠️ Неверный ввод. Попробуйте снова.",
        Language.uz: "⚠️ Noto'g'ri kiritish. Qaytadan urinib ko'ring.",
    },

    "user_not_found": {
        Language.en: "❌ User not found. Please /start the bot first.",
        Language.ru: "❌ Пользователь не найден. Пожалуйста, запустите бот с /start.",
        Language.uz: "❌ Foydalanuvchi topilmadi. Iltimos, /start bilan boshlang.",
    },

    # ========================================================================
    # HELP MESSAGES
    # ========================================================================
    "help_text": {
        Language.en: "ℹ️ Help\n\nAvailable commands:\n/start - Start the bot\n/cancel - Cancel current operation\n/clear - Clear chat history\n/admin - Admin panel (admins only)\n\nFor support, contact @O_Mirzabek",
        Language.ru: "ℹ️ Помощь\n\nДоступные команды:\n/start - Запустить бота\n/cancel - Отменить текущую операцию\n/clear - Очистить историю чата\n/admin - Панель администратора (только для админов)\n\nПоддержка: @O_Mirzabek",
        Language.uz: "ℹ️ Yordam\n\nMavjud buyruqlar:\n/start - Botni boshlash\n/cancel - Joriy amalni bekor qilish\n/clear - Suhbat tarixini tozalash\n/admin - Admin paneli (faqat adminlar)\n\nQo'llab-quvvatlash: @O_Mirzabek",
    },
}


# ============================================================================
# MESSAGE RETRIEVAL FUNCTION
# ============================================================================

def get_message(key: str, lang: Language, **kwargs) -> str:
    """
    Get localized message by key.

    Args:
        key: Message key from _MESSAGES dict
        lang: Language to use
        **kwargs: Format parameters for message

    Returns:
        Formatted localized message

    Raises:
        KeyError: If message key doesn't exist
    """
    if key not in _MESSAGES:
        raise KeyError(f"❌ Unknown message key: {key}")

    messages = _MESSAGES[key]
    msg = messages.get(lang, messages.get(Language.en, "Message not found"))

    if kwargs:
        try:
            return msg.format(**kwargs)
        except KeyError as e:
            # Log error but return unformatted message
            import logging
            logging.error(f"❌ Missing format parameter in message '{key}': {e}")
            return msg

    return msg


def get_all_languages() -> list:
    """Get list of all supported languages."""
    return [Language.en, Language.ru, Language.uz]


def add_message(key: str, translations: dict) -> None:
    """
    Add a new message dynamically.

    Args:
        key: Message key
        translations: Dict with Language keys and message values

    Example:
        add_message("new_feature", {
            Language.en: "New feature!",
            Language.ru: "Новая функция!",
            Language.uz: "Yangi funksiya!"
        })
    """
    _MESSAGES[key] = translations


def message_exists(key: str) -> bool:
    """Check if a message key exists."""
    return key in _MESSAGES


def get_all_message_keys() -> list:
    """Get all available message keys."""
    return list(_MESSAGES.keys())
