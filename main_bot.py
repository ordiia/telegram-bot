import random
import logging
import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)

import os
BOT_TOKEN = "8007679799:AAGekKeFh9L9oWLI35ieOM3ENjCxCKofJow"
ADMIN_CHAT_ID = "-4618714192"  # Chat ID where you want logs
PARTICIPANT_FILE = "participan.json"  # Stores unique participant numbers

# === UTILS ===
def load_participants():
    try:
        with open(PARTICIPANT_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_participants(data):
    with open(PARTICIPANT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def generate_unique_number(existing_ids):
    while True:
        number = f"P{random.randint(1000, 9999)}"
        if number not in existing_ids:
            return number

# === START COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    participants_data = load_participants()

    if str(chat_id) in participants_data:
        await context.bot.send_message(chat_id=chat_id, text="Ви вже зареєстровані!")
        return

    new_id = generate_unique_number([p["id"] for p in participants_data.values()])
    participants_data[str(chat_id)] = {
        "id": new_id,
        "joined_at": datetime.now().isoformat(),
        "task_done": False
    }
    save_participants(participants_data)

    await context.bot.send_message(chat_id=chat_id, text=f"Привіт! Ваш анонімний номер учасника: {new_id}")
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Учасник {new_id} приєднався.")

    context.job_queue.run_once(send_test_message, when=5, chat_id=chat_id)
    context.job_queue.run_once(ask_if_done, when=20, chat_id=chat_id)

async def send_test_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(chat_id=chat_id, text="""\
Вітаю! Дякую за участь у цьому дослідженні!

На цій сторінці Ви зможете прочитати короткий опис дослідження та те, що потрібно виконати перш ніж переходити до самого завдання.

У цьому дослідженні Вам буде потрібно писати на одну із заданих тем 15 хвилин та заповнити анкету до і після експерименту. Усі дані будуть конфіденційними, а Ваші записи будуть доступні лише Вам.

Перед виконанням завдань, будь ласка:
• Заповніть це опитування (https://docs.google.com/forms/d/e/1FAIpQLSdqW48eEaLW27ax2iQ-NfXQ2VT1Uw-7cNlPzVeqEfH5Lgcetg/viewform?usp=header)
• Зверніть увагу, що ця техніка може бути досить емоційною, і деякі люди плакали під час її виконання
• Краще мати ці інструкції під рукою під час експерименту.

ВАЖЛИВО: будь ласка, не обговорюйте ні з ким письмову техніку та деталі своїх інструкцій.
""")

async def ask_if_done(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(chat_id=chat_id, text="Чи виконали ви перше завдання? (Відповідайте: так / ні)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    chat_id = update.effective_chat.id
    participants_data = load_participants()
    user = participants_data.get(str(chat_id), None)

    if not user:
        return

    if "так" in text:
        user["task_done"] = True
        await context.bot.send_message(chat_id=chat_id, text="Чудово! Очікуйте інших учасників.")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Учасник {user['id']} виконав перше завдання.")
        save_participants(participants_data)

    elif "ні" in text:
        await context.bot.send_message(chat_id=chat_id, text="Будь ласка, поверніться до гугл форми та заповніть її.")
        context.job_queue.run_once(ask_if_done, when=40, chat_id=chat_id)

async def assign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Використання: /assign P1234 текст_повідомлення")
        return

    participant_id = args[0]
    message_text = " ".join(args[1:])
    participants_data = load_participants()

    for chat_id, data in participants_data.items():
        if data["id"] == participant_id:
            await context.bot.send_message(chat_id=int(chat_id), text=message_text)
            await update.message.reply_text(f"✅ Повідомлення надіслано до {participant_id}")
            return

    await update.message.reply_text("❌ Учасник не знайдений.")

async def clear_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    participants_data = load_participants()

    if str(chat_id) in participants_data:
        del participants_data[str(chat_id)]
        save_participants(participants_data)
        await update.message.reply_text("✅ Ви були видалені з реєстрації.")
    else:
        await update.message.reply_text("❌ Ви не зареєстровані у системі.")

def main():
    app = ApplicationBuilder().token("8007679799:AAGekKeFh9L9oWLI35ieOM3ENjCxCKofJow").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("assign", assign))
    app.add_handler(CommandHandler("clearme", clear_me))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
