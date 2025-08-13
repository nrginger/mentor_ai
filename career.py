import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from requests.exceptions import ReadTimeout, RequestException

load_dotenv()
ENDPOINT = os.getenv('ENDPOINT').rstrip('/')
API_KEY   = os.getenv('API_KEY')
MODEL     = 'deepseek-chat'

# Типы вопросов по шагам
QUESTION_TYPES = {
    1: "вопрос о проектах пользователя в области этой профессии (учебных или рабочих)",
    2: "технический вопрос по специальности",
    3: "технический вопрос по специальности",
    4: "технический вопрос по специальности",
    5: "поведенческий (soft skills) вопрос о командной работе или коммуникации"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализация режима 'Карьера' — спрашиваем должность."""
    context.user_data.clear()
    context.user_data['career_step'] = 0
    with open('images/cat_career.png', 'rb') as img:
        await update.callback_query.message.reply_photo(
            photo=img,
            caption="На какую должность ты хочешь устроиться?"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов: по шагам задаём вопросы и в конце – анализ."""
    step = context.user_data.get('career_step', 0)
    text = update.message.text.strip()

    # Шаг 0: сохраняем должность, переходим к первому вопросу
    if step == 0:
        context.user_data['career_position'] = text
        context.user_data['career_history'] = []
        context.user_data['career_step'] = 1
    else:
        # сохраняем ответ на предыдущий вопрос
        context.user_data['career_history'].append({
            "role": "user",
            "content": text
        })
        context.user_data['career_step'] += 1

    step = context.user_data['career_step']

    # 1–5: задаём следующий вопрос
    if 1 <= step <= 5:
        q_type = QUESTION_TYPES[step]
        position = context.user_data['career_position']
        system_prompt = (
            f"Ты — AI-интервьюер уровня Junior. "
            "Обращайся к пользователю на 'ты'. "
            f"Должность кандидата: «{position}». "
            f"Твой **единственный** ответ должен быть **вопросительным предложением** — "
            f"ни слова благодарности, ни вводных фраз, ни пояснений. "
            f"Просто задай **один {q_type}**."

        )
        messages = [{"role": "system", "content": system_prompt}]
        messages += context.user_data['career_history']

        try:
            resp = requests.post(
                f"{ENDPOINT}/chat/completions",
                json={"model": MODEL, "messages": messages},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=(5, 60)  # 5 сек на соединение, 60 сек на чтение
            )
            resp.raise_for_status()
        except ReadTimeout:
            await update.message.reply_text(
                "Сервер не ответил в течение 60 секунд. Попробуйте чуть позже."
            )
            return
        except RequestException as e:
            await update.message.reply_text(f"Ошибка при запросе вопроса: {e}")
            return

        question = resp.json()["choices"][0]["message"]["content"]
        context.user_data['career_history'].append({
            "role": "assistant",
            "content": question
        })
        await update.message.reply_text(question)
        return

    # Шаг 6: все 5 ответов собраны — формируем анализ
    position = context.user_data['career_position']
    answers = [
        m["content"] for m in context.user_data['career_history']
        if m["role"] == "user"
    ]
    analysis_prompt = (
        f"Кандидат претендует на должность «{position}».\n\n"
        "Вот его ответы на пять вопросов:\n" +
        "\n".join(f"{i+1}) {ans}" for i, ans in enumerate(answers)) +
        "\n\nДай развёрнутый анализ по техническим знаниям, "
        "коммуникации и самопрезентации, а также рекомендации для улучшения."
    )
    messages = [
        {"role": "system", "content": (
            "Ты — AI-интервьюер. В **единственном** сообщении дай **только** анализ ответов "
            "и практические рекомендации — без «здравствуйте», «спасибо» и прочих вступлений."
            "Обращайся к пользователю на 'ты'. "
        )},
        {"role": "user", "content": analysis_prompt}
    ]

    try:
        resp = requests.post(
            f"{ENDPOINT}/chat/completions",
            json={"model": MODEL, "messages": messages},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=(10, 120)
        )
        resp.raise_for_status()
    except ReadTimeout:
        await update.message.reply_text(
            "Сервер не ответил на анализ в течение 2 минут. Попробуйте позже."
        )
        return
    except RequestException as e:
        await update.message.reply_text(f"Ошибка при запросе анализа: {e}")
        return

    analysis = resp.json()["choices"][0]["message"]["content"]
    await update.message.reply_text(analysis)

    # Сброс, чтобы можно было запустить заново
    context.user_data['career_step'] = 0
