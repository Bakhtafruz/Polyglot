import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8881375442:AAFUYe8I4HDRkvEC50whvVa_W-OH4RFu27Y"
ADMIN_CHAT_ID = 7505210449  # Ваш ID администратора

NAME, PHONE = range(2)
TEST_Q1, TEST_Q2 = range(2, 4)
BROADCAST_TEXT = 10  # Состояние для ожидания текста рассылки

# Множество для подсчета активных пользователей
users_db = set()

# --- НАСТРОЙКА GOOGLE ТАБЛИЦ (Необязательно, если файл настроен) ---
def save_to_google_sheet(name, phone, username):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        # Укажите точное название вашей таблицы в Google Drive
        sheet = client.open("Polyglot Academy Leads").sheet1 
        sheet.append_row([name, phone, username])
    except Exception as e:
        print(f"Ошибка Google Таблиц (проверьте credentials.json): {e}")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    users_db.add(chat_id)

    lang_keyboard = [
        ["🇷🇺 Русский", "🇬🇧 English"]
    ]
    reply_markup = ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True)

    welcome_text = (
        "✨ <b>Polyglot Academy</b> ✨\n"
        "🚀 <i>Your future starts here!</i>\n\n"
        "🎓 Откройте мир новых возможностей вместе с нами!\n"
        "👤 <b>Директор:</b> Меликов Б. З.\n\n"
        "👉 <b>Выберите язык интерфейса / Choose your language:</b>"
    )

    animation_path = "logo_animation.mp4"
    photo_path = "photo.jpg"
    
    if os.path.exists(animation_path):
        with open(animation_path, 'rb') as anim:
            await update.message.reply_animation(animation=anim, caption=welcome_text, parse_mode="HTML", reply_markup=reply_markup)
    elif os.path.exists(photo_path):
        with open(photo_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=welcome_text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=reply_markup)

# Главное меню (Русский язык)
async def main_menu_ru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lang'] = 'ru'
    keyboard = [
        ["📅 Расписание", "💰 Стоимость"],
        ["🚀 Записаться на урок", "💳 Оплата"],
        ["📸 Фото и видео", "🎯 Тест на уровень"],
        ["❓ FAQ (Вопросы)", "⭐ Отзывы"],
        ["📲 QR-код бота", "📍 Наш адрес"],
        ["ℹ️ О нас", "📞 Контакты"],
        ["🌐 Сменить язык"]
    ]
    
    # Добавляем кнопку админ-панели, если пишет директор/админ
    if update.effective_chat.id == ADMIN_CHAT_ID:
        keyboard.append(["🛠️ Админ-панель"])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🔥 <b>Добро пожаловать в Главное меню!</b>\n\n"
        "Выбирай нужный раздел и делай шаг к свободному английскому прямо сейчас! 👇",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Главное меню (Английский язык)
async def main_menu_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lang'] = 'en'
    keyboard = [
        ["📅 Schedule", "💰 Price"],
        ["🚀 Register Now", "💳 Payment"],
        ["📸 Photos & Videos", "🎯 Level Test"],
        ["❓ FAQ", "⭐ Reviews"],
        ["📲 Bot QR-Code", "📍 Location"],
        ["ℹ️ About us", "📞 Contacts"],
        ["🌐 Change Language"]
    ]
    
    if update.effective_chat.id == ADMIN_CHAT_ID:
        keyboard.append(["🛠️ Admin Panel"])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🔥 <b>Welcome to Main Menu!</b>\n\n"
        "Choose an option below and start learning today! 👇",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# --- ИНТЕРАКТИВНАЯ АДМИН-ПАНЕЛЬ ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="btn_broadcast")],
        [InlineKeyboardButton("📊 Статистика бота", callback_data="btn_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠️ <b>Панель управления администратора:</b>\nВыберите действие:", parse_mode="HTML", reply_markup=reply_markup)

# Обработка нажатий кнопок админ-панели
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_stats":
        total_users = len(users_db)
        await query.message.reply_text(f"📊 <b>Статистика бота:</b>\n\n👥 Всего уникальных пользователей запустили бота: <b>{total_users}</b>", parse_mode="HTML")
    
    elif query.data == "btn_broadcast":
        await query.message.reply_text("✍️ Введите текст для массовой рассылки подписчикам одним сообщением:")
        return BROADCAST_TEXT

# Шаг получения текста для рассылки через админ-панель
async def receive_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_send = update.message.text
    count = 0
    failed = 0

    for uid in users_db:
        try:
            await context.bot.send_message(
                chat_id=uid, 
                text=f"📢 <b>Объявление от Polyglot Academy:</b>\n\n{text_to_send}", 
                parse_mode="HTML"
            )
            count += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ Рассылка завершена!\n\n📨 Успешно: {count}\n❌ Заблокировали бота: {failed}")
    return ConversationHandler.END

# --- ТЕСТ НА УРОВЕНЬ ---
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['score'] = 0
    keyboard = [
        ["a) am", "b) is"],
        ["c) are", "d) be"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "🎯 <b>Тест на уровень (Вопрос 1 из 2):</b>\n\n"
        "Выберите правильный вариант:\n"
        "<i>I _ a student.</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return TEST_Q1

async def test_q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if "a" in answer.lower():
        context.user_data['score'] += 1

    keyboard = [
        ["a) go", "b) goes"],
        ["c) going", "d) went"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "🎯 <b>Вопрос 2 из 2:</b>\n\n"
        "Выберите правильный вариант:\n"
        "<i>He usually _ to work by car.</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return TEST_Q2

async def test_q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    if "b" in answer.lower():
        context.user_data['score'] += 1

    score = context.user_data['score']
    
    if score == 2:
        result_text = "🌟 <b>Отличный результат!</b> Вам подойдет уровень <b>Pre-Intermediate</b> или <b>Intermediate</b>."
    elif score == 1:
        result_text = "👍 <b>Хороший результат!</b> Вам идеально подойдет уровень <b>Elementary</b>."
    else:
        result_text = "📚 <b>Начальный уровень.</b> Рекомендуем начать с курса <b>Beginner</b>."

    await update.message.reply_text(
        f"🏁 <b>Тест завершен!</b>\n\n{result_text}\n\n👉 <i>Сделайте следующий шаг — запишитесь на бесплатный пробный урок!</i>",
        parse_mode="HTML"
    )
    return ConversationHandler.END

# --- ЗАПИСЬ НА ПРОБНЫЙ УРОК ---
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 <b>Запись на бесплатный пробный урок</b>\n\n"
        "Инвестируйте в свое будущее уже сегодня! Напишите ваше <b>Имя</b>:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        f"Приятно познакомиться, <b>{context.user_data['name']}</b>! 👋\n\n"
        "Теперь введите ваш <b>номер телефона</b> для связи:",
        parse_mode="HTML"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = context.user_data['name']
    user_phone = update.message.text
    user_username = f"@{update.effective_user.username}" if update.effective_user.username else "нет юзернейма"

    await update.message.reply_text(
        "✅ <b>Отлично! Заявка успешно принята.</b>\n"
        "Наш менеджер свяжется с вами в течение 15 минут!",
        parse_mode="HTML"
    )

    # Отправка администратору в Telegram
    try:
        admin_message = f"🔥 <b>НОВАЯ ЗАЯВКА НА УРОК!</b>\n\n👤 Имя: {user_name}\n📞 Телефон: {user_phone}\n💬 Telegram: {user_username}"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    # Сохранение в Google Таблицы (автоматически)
    save_to_google_sheet(user_name, user_phone, user_username)

    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Запись отменена.")
    return ConversationHandler.END

# --- ОБРАБОТКА СООБЩЕНИЙ И КНОПОК ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    users_db.add(chat_id)
    text = update.message.text.lower()

    if "русский" in text:
        await main_menu_ru(update, context)
        return
    elif "english" in text:
        await main_menu_en(update, context)
        return
    elif "сменить язык" in text or "change language" in text or "change language" in text:
        await start(update, context)
        return
    elif "админ-панель" in text or "admin panel" in text:
        if chat_id == ADMIN_CHAT_ID:
            await admin_panel(update, context)
        return

    elif "qr" in text or "кьюар" in text:
        qr_path = "qr_code.png"
        caption_text = (
            "📲 <b>QR-код бота Polyglot Academy</b>\n\n"
            "Поделитесь им с друзьями и знакомыми! Пусть они тоже учат английский легко и с удовольствием. 🚀"
        )
        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as qr:
                await update.message.reply_photo(photo=qr, caption=caption_text, parse_mode="HTML")
        else:
            await update.message.reply_text(
                f"{caption_text}\n\n🔗 Ссылка на бота: t.me/ваш_бот",
                parse_mode="HTML"
            )

    elif "расписание" in text or "schedule" in text:
        await update.message.reply_text(
            "📅 <b>Расписание занятий:</b>\n\n"
            "• <b>Beginner:</b> Пн / Ср / Пт — 10:00 - 11:30\n"
            "• <b>Elementary:</b> Вт / Чт / Сб — 14:00 - 15:30\n"
            "• <b>Pre-Intermediate:</b> Пн / Ср / Пт — 13:00 - 15:00\n"
            "• <b>Intermediate:</b> Пн / Ср / Пт — 16:00 - 18:00\n"
            "• 🗣️ <b>Speaking Club:</b> Суббота — 16:00",
            parse_mode="HTML"
        )
    elif "стоимость" in text or "price" in text:
        await update.message.reply_text(
            "💎 <b>Стоимость обучения в Polyglot Academy:</b>\n\n"
            "🔥 <b>Всего 200 сомони в месяц</b> за любой курс!\n\n"
            "📚 Все учебники и материалы — <b>БЕСПЛАТНО</b>!\n"
            "🎁 Первый пробный урок — <b>БЕСПЛАТНО</b>!\n\n"
            "👉 Нажмите <i>«Записаться на урок»</i>, чтобы забронировать место!",
            parse_mode="HTML"
        )
    elif "оплата" in text or "payment" in text:
        bank_text = (
            "💳 <b>Реквизиты для оплаты:</b>\n\n"
            "🏦 Банк: <b>IBT24</b>\n"
            "📱 Кошелек / Телефон: <code>+992019627373</code>\n"
            "📋 Номер счета: <code>20216972901022590002</code>\n"
            "🏛️ БИК: 350101803\n"
            "👤 Получатель: Polyglot Academy / Бахтафруз З.\n\n"
            "📌 <i>После оплаты отправьте скрин чека администратору:</i> @polyglot_admin"
        )
        await update.message.reply_text(bank_text, parse_mode="HTML")
    elif "о нас" in text or "about" in text:
        about_text = (
            "✨ <b>Polyglot Academy</b> ✨\n"
            "🚀 <i>Your future starts here!</i>\n\n"
            "👤 <b>Директор:</b> Меликов Б. З.\n\n"
            "Мы создаем идеальную среду для быстрого и уверенного изучения английского языка. Записывайтесь и развивайтесь вместе с нами!"
        )
        inline_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Наш Instagram", url="https://instagram.com/bakhtafruz_z.m")],
            [InlineKeyboardButton("💬 Написать администратору", url="https://t.me/polyglot_admin")]
        ])
        await update.message.reply_text(about_text, parse_mode="HTML", reply_markup=inline_kb)
    elif "контакт" in text or "contacts" in text:
        contacts_text = (
            "📞 <b>Контакты и Локация:</b>\n\n"
            "🏢 <b>Polyglot Academy</b>\n"
            "📍 Адрес: Шахринавский район, село Аджам\n"
            "📞 Телефон: +992019627373\n"
            "⏰ График: Пн-Сб с 08:00 до 18:00\n\n"
            "👉 Ждем вас на уроках!"
        )
        inline_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Instagram", url="https://instagram.com/bakhtafruz_z.m")],
            [InlineKeyboardButton("💬 Telegram", url="https://t.me/polyglot_admin")]
        ])
        await update.message.reply_text(contacts_text, parse_mode="HTML", reply_markup=inline_kb)
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки меню ниже 👇")

# Запуск бота
def main():
    app = Application.builder().token(TOKEN).build()

    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("(?i)(записаться|register)"), start_registration)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )

    test_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("(?i)(тест|level test)"), start_test)],
        states={
            TEST_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_q1)],
            TEST_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_q2)],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )

    broadcast_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("(?i)админ-панель|admin panel"), admin_panel)
        ],
        states={
            BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_handler)
    app.add_handler(test_handler)
    app.add_handler(broadcast_handler)
    
    # Обработчик callback-нажатий на кнопки админ-панели
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(admin_callback))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Супер-бот Polyglot Academy запущен со всеми расширенными функциями!")
    app.run_polling()

if __name__ == "__main__":
    main()