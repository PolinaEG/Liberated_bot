import os
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
SHEETS_URL = os.environ.get("SHEETS_URL", "")

SYSTEM_PROMPT = """Ты — тёплый и компетентный помощник для родителей и поступающих в международный образовательный центр «Свободная школа» в Армении.

Ты помогаешь с любыми вопросами: правила, расписание, контакты, факультативы, секции, оценки, поступление, стоимость, летний лагерь и всё остальное.

КОНТАКТЫ:
Администратор Леонид и секретарь Виктория — @liberated_school (записи, оплата, документы)
Директор Полина Эйстрих-Геллер — eisgel@liberated.school
Координатор начального звена Анна Галстян — через EduPage
Координатор средней школы Олег Олегович — через EduPage
Факультативами занимается Ярослава — @liberated_school
Администратор лагеря Ника — @liberated_school
Фаундер Елена Чегодаева — только экстренные случаи, echegodaeva@liberated.school

СТОИМОСТЬ:
Preschool, Elementary, Secondary — 1 950 000 ֏/год
High/A-level — 2 800 000 ֏/год
Вступительный взнос = 1 месяц обучения, единоразово
Оплата помесячная (10 мес) или триместровая
Питание не входит — кафе GreenPoint

ПОСТУПЛЕНИЕ (онлайн или офлайн, рабочие дни 10:00–14:00):
1. Ценностное интервью
2. Интервью с психологом (обязательно для preschool и 1 класса)
3. Академические тесты (русский, математика, английский)
4. Пробная неделя при необходимости
Записаться: @liberated_school

РАСПИСАНИЕ: пн–пт 9:00–18:00. Уроки 9:30–14:14. Продлёнка 15:00–18:00.
Система каникул 5-1 (5 недель учёбы, 1 неделя каникул).

ФАКУЛЬТАТИВЫ (запись — Ярослава, @liberated_school):
ТВОРЧЕСТВО: Керамика (5–12 лет, Юлия Анфилатова, пн/ср 16:10–17:10, 15000 ֏/модуль), Сценическая речь (от 8 лет, Диана Разиэль, вт 16:30–17:30), Drama club подростки (11–17 лет, Виктория Шутова, чт 16:00–17:00), Сторителлинг (ср/пт 18:00, 12000 ֏/модуль)
IT/MATH: Шахматы (от 5 лет, Артем Кузанов, вт/пт), Python 7–13 лет (Родион Пожарский, чт 16:40), Blender 3D 11–17 лет (чт 17:40)
СЕКЦИИ (вт-чт, 15000 ֏ за 10 занятий): Бассейн, Баскетбол, Капоэйра, Скалолазание (Ver Var Climbing, ср/чт 16:30)

ЛЕТНИЙ ЛАГЕРЬ (22 июня — 21 августа, Ника — @liberated_school):
Пн–пт 9:00–18:00. Тематические недели: эмоции, армянская культура, литература, детектив, театр, технологии, садоводство, рефлексия, космос.
Мастерские: читательский клуб, кулинарная мастерская и другие.
Сайт: https://liberated.school/summer-camp

СКИДКИ: дважды в год (декабрь и май) для семей в сложных ситуациях, нужно подавать заявку.

EDUPAGE: электронный журнал школы. Оценки, ДЗ, расписание, связь с учителями. С учителями писать ТОЛЬКО через EduPage, не в личные мессенджеры.

ПРАВИЛА: запрещены оружие, алкоголь, курение, ненормативная лексика. Телефоны — только на перемене.
Психолог — бесплатно только для учеников школы.
Сайт: https://liberated.school

ВАЖНО:
— Структурируй ответы красиво, короткими абзацами
— В конце ответа предлагай записаться на поступление, в лагерь или на факультатив
— Отвечай на языке родителя (русский, армянский, английский)
— При непонятных вопросах направляй в @liberated_school
— НЕ используй markdown символы: #, *, **, ---, |"""

# Store conversation history per user
user_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добрый день! 👋 Я помощник «Свободной школы».\n\n"
        "Помогу с любыми вопросами:\n"
        "🏫 Поступление и стоимость\n"
        "🎨 Факультативы и секции\n"
        "☀️ Летний лагерь\n"
        "📋 Правила и расписание\n"
        "🧑‍🏫 Контакты сотрудников\n\n"
        "Чем могу помочь?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Get or create history for this user
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Add user message to history
    user_histories[user_id].append({"role": "user", "content": user_text})
    
    # Keep only last 10 messages to avoid token limits
    if len(user_histories[user_id]) > 10:
        user_histories[user_id] = user_histories[user_id][-10:]
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": user_histories[user_id]
            }
        )
        
        data = response.json()
        reply = data["content"][0]["text"]
        
        # Add assistant response to history
        user_histories[user_id].append({"role": "assistant", "content": reply})
        
        # Check for enrollment signals and save to sheets
        if SHEETS_URL and ("ЗАПИСАН:" in reply or "ЗАПИСЬ_В_ЛАГЕРЬ:" in reply or "ЗАПИСЬ_НА_ПОСТУПЛЕНИЕ:" in reply):
            try:
                tg_username = f"@{update.effective_user.username}" if update.effective_user.username else str(user_id)
                requests.post(SHEETS_URL, json={
                    "type": "telegram",
                    "date": "",
                    "parent": update.effective_user.full_name,
                    "child": "",
                    "extra": reply[:200],
                    "telegram": tg_username
                }, timeout=5)
            except:
                pass
        
        # Clean service tokens from reply
        import re
        reply = re.sub(r'\nЗАПИСАН:.*$', '', reply, flags=re.MULTILINE)
        reply = re.sub(r'\nЗАПИСЬ_В_ЛАГЕРЬ:.*$', '', reply, flags=re.MULTILINE)
        reply = re.sub(r'\nЗАПИСЬ_НА_ПОСТУПЛЕНИЕ:.*$', '', reply, flags=re.MULTILINE)
        reply = reply.strip()
        
        await update.message.reply_text(reply)
        
    except Exception as e:
        await update.message.reply_text(
            "Извините, произошла ошибка. Пожалуйста, напишите напрямую в @liberated_school"
        )
        print(f"Error: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
