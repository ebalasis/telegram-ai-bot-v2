import os
import logging
import asyncio
import psycopg2
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode  # Διορθωμένο
from aiogram.client.default import DefaultBotProperties  # Προσθέτουμε αυτή τη γραμμή!
from aiogram.filters import Command  # Νέα εισαγωγή για commands
from datetime import datetime, timedelta
from database import connect_db, setup_database
import re

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')  # Διορθωμένο!

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# Συνάρτηση για να αποθηκεύει υπενθυμίσεις
async def save_reminder(user_id, message, reminder_time, repeat_interval=None):
    conn, cursor = connect_db()
    cursor.execute(
        "INSERT INTO reminders (user_id, message, reminder_time, repeat_interval) VALUES (%s, %s, %s, %s)",
        (user_id, message, reminder_time, repeat_interval)
    )
    conn.commit()
    cursor.close()
    conn.close()

# Συνάρτηση που ελέγχει και στέλνει υπενθυμίσεις
async def check_reminders():
    while True:
        conn, cursor = connect_db()
        now = datetime.now()
        cursor.execute("SELECT id, user_id, message, repeat_interval FROM reminders WHERE reminder_time <= %s", (now,))
        reminders = cursor.fetchall()

        for reminder in reminders:
            reminder_id, user_id, message, repeat_interval = reminder
            await bot.send_message(user_id, f"🔔 Υπενθύμιση: {message}")

            if repeat_interval:
                next_time = now + timedelta(seconds=repeat_interval)
                cursor.execute("UPDATE reminders SET reminder_time = %s WHERE id = %s", (next_time, reminder_id))
            else:
                cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
            conn.commit()

        cursor.close()
        conn.close()
        await asyncio.sleep(60)  # Έλεγχος κάθε λεπτό

# Χειριστής εντολής /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Γεια σου! Στείλε /remind [χρόνος] [μονάδα χρόνου] [μήνυμα] για να αποθηκεύσεις μια υπενθύμιση. Π.χ. /remind 2 ώρες Να πάρω τηλέφωνο.")

# Συνάρτηση για μετατροπή χρόνου
TIME_UNITS = {
    "λεπτό": 60, "λεπτά": 60, "λεπτ": 60,
    "ώρα": 3600, "ώρες": 3600,
    "μέρα": 86400, "μέρες": 86400,
    "εβδομάδα": 604800, "εβδομάδες": 604800,
    "μήνα": 2592000, "μήνες": 2592000,
    "χρόνος": 31536000, "χρόνια": 31536000
}

def parse_time_input(time_str, unit):
    if unit in TIME_UNITS:
        return int(time_str) * TIME_UNITS[unit]
    return None

# Χειριστής εντολής /remind
@router.message(Command("remind"))
async def remind_command(message: types.Message):
    try:
        args = message.text.split(maxsplit=3)
        if len(args) < 4:
            raise ValueError("❌ Χρήση: /remind <αριθμός> <μονάδα χρόνου> <μήνυμα>")

        time_value = args[1]
        time_unit = args[2]
        reminder_text = args[3]
        
        seconds = parse_time_input(time_value, time_unit)
        if seconds is None:
            raise ValueError("❌ Μη έγκυρη μονάδα χρόνου. Δοκίμασε λεπτά, ώρες, μέρες, μήνες, χρόνια.")

        reminder_time = datetime.now() + timedelta(seconds=seconds)
        await save_reminder(message.from_user.id, reminder_text, reminder_time)
        await message.answer(f"✅ Υπενθύμιση αποθηκεύτηκε! Θα λάβεις το μήνυμα σε {time_value} {time_unit}.")

    except ValueError as e:
        await message.answer(str(e))

# Εκκίνηση της υπενθύμισης στο παρασκήνιο
async def main():
    dp.include_router(router)  # Προσθέτουμε τα handlers
    asyncio.create_task(check_reminders())  # Ξεκινάμε την υπενθύμιση στο background
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
