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
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Γεια σου! Στείλε /remind [χρόνος σε λεπτά] [μήνυμα] για να αποθηκεύσεις μια υπενθύμιση.")

# Χειριστής εντολής /remind
@router.message(Command("remind"))
async def remind_command(message: types.Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise ValueError("❌ Χρήση: /remind <λεπτά> <μήνυμα>")

        minutes = int(args[1])
        reminder_text = args[2]
        reminder_time = datetime.now() + timedelta(minutes=minutes)

        await save_reminder(message.from_user.id, reminder_text, reminder_time)
        await message.answer(f"✅ Υπενθύμιση αποθηκεύτηκε! Θα λάβεις το μήνυμα σε {minutes} λεπτά.")

    except ValueError as e:
        await message.answer(str(e))

# Χειριστής εντολής /list_reminders
@router.message(Command("list_reminders"))
async def list_reminders(message: types.Message):
    conn, cursor = connect_db()
    cursor.execute("SELECT id, message, reminder_time FROM reminders WHERE user_id = %s ORDER BY reminder_time ASC", (message.from_user.id,))
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()

    if not reminders:
        await message.answer("🔹 Δεν έχεις αποθηκευμένες υπενθυμίσεις.")
        return

    response = "📌 Οι υπενθυμίσεις σου:\n"
    for reminder in reminders:
        reminder_id, reminder_text, reminder_time = reminder
        formatted_time = reminder_time.strftime("%Y-%m-%d %H:%M")
        response += f"🆔 {reminder_id} | {formatted_time} - {reminder_text}\n"

    await message.answer(response)

# Χειριστής εντολής /delete_reminder
@router.message(Command("delete_reminder"))
async def delete_reminder(message: types.Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("❌ Χρήση: /delete_reminder <ID>")
        
        reminder_id = int(args[1])
        conn, cursor = connect_db()
        cursor.execute("DELETE FROM reminders WHERE id = %s AND user_id = %s RETURNING id", (reminder_id, message.from_user.id))
        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted:
            await message.answer(f"🗑️ Η υπενθύμιση με ID {reminder_id} διαγράφηκε επιτυχώς.")
        else:
            await message.answer("⚠️ Δεν βρέθηκε υπενθύμιση με αυτό το ID.")
    except ValueError:
        await message.answer("❌ Το ID πρέπει να είναι αριθμός.")

# Εκκίνηση της υπενθύμισης στο παρασκήνιο
async def main():
    dp.include_router(router)  # Προσθέτουμε τα handlers
    asyncio.create_task(check_reminders())  # Ξεκινάμε την υπενθύμιση στο background
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
