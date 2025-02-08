import os
import logging
import asyncio
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.utils import executor
from datetime import datetime, timedelta
from database import connect_db, setup_database

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('postgresql://postgres:jitvcjHcHnWKoMVDMXGPcJhFdukRjukO@roundhouse.proxy.rlwy.net:51799/railway')

# Δημιουργία bot και dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Συνάρτηση για να αποθηκεύει υπενθυμίσεις
async def save_reminder(user_id, message, reminder_time):
    conn, cursor = connect_db()
    cursor.execute(
        "INSERT INTO reminders (user_id, message, reminder_time) VALUES (%s, %s, %s)",
        (user_id, message, reminder_time)
    )
    conn.commit()
    cursor.close()
    conn.close()

# Συνάρτηση που ελέγχει και στέλνει υπενθυμίσεις
async def check_reminders():
    while True:
        conn, cursor = connect_db()
        now = datetime.now()
        cursor.execute("SELECT id, user_id, message FROM reminders WHERE reminder_time <= %s", (now,))
        reminders = cursor.fetchall()

        for reminder in reminders:
            reminder_id, user_id, message = reminder
            await bot.send_message(user_id, f"🔔 Υπενθύμιση: {message}")

            # Διαγραφή μετά την αποστολή
            cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
            conn.commit()

        cursor.close()
        conn.close()
        await asyncio.sleep(60)  # Έλεγχος κάθε λεπτό

# Χειριστής εντολής /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply("👋 Γεια σου! Στείλε /remind <χρόνος σε λεπτά> <μήνυμα> για να αποθηκεύσεις μια υπενθύμιση.")

# Χειριστής εντολής /remind
@dp.message_handler(commands=['remind'])
async def remind_command(message: types.Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise ValueError("❌ Χρήση: /remind <λεπτά> <μήνυμα>")

        minutes = int(args[1])
        reminder_text = args[2]
        reminder_time = datetime.now() + timedelta(minutes=minutes)

        await save_reminder(message.from_user.id, reminder_text, reminder_time)
        await message.reply(f"✅ Υπενθύμιση αποθηκεύτηκε! Θα λάβεις το μήνυμα σε {minutes} λεπτά.")

    except ValueError as e:
        await message.reply(str(e))

# Εκκίνηση της υπενθύμισης στο παρασκήνιο
loop = asyncio.get_event_loop()
loop.create_task(check_reminders())

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
