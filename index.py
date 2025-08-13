import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

import study
import career

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Загрузка .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start: показываем приветствие и две кнопки."""
    keyboard = [
        [
            InlineKeyboardButton("Учёба", callback_data='study'),
            InlineKeyboardButton("Карьера", callback_data='career'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Отправляем картинку и текст
    with open('images/cat_start.png', 'rb') as img:
        await update.message.reply_photo(
            photo=img,
            caption=(
                "Привет, я — MentorAI, помогу тебе разобраться с учебными заданиями "
                "без готовых ответов или подготовиться к собеседованию, чтобы устроиться "
                "на работу мечты! Выбери подходящий режим:"
            ),
            reply_markup=reply_markup
        )

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутинг на сценарии 'Учёба' и 'Карьера' по нажатию кнопки."""
    query = update.callback_query
    await query.answer()
    if query.data == 'study':
        await study.start(update, context)
        context.user_data['mode'] = 'study'
    elif query.data == 'career':
        await career.start(update, context)
        context.user_data['mode'] = 'career'

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений: делегируем в study или career по mode."""
    mode = context.user_data.get('mode')
    if mode == 'study':
        await study.handle_message(update, context)
    elif mode == 'career':
        await career.handle_message(update, context)
    else:
        await update.message.reply_text("Нажмите /start, чтобы выбрать режим работы бота.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Хэндлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

    # Запуск
    logging.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
