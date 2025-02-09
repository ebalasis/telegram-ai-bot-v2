import os
import logging
import asyncio
import psycopg2
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from datetime import datetime, timedelta
from database import connect_db, setup_database

# Ρύθμιση logging για debugging
logging.basicConfig(level=logging.INFO)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# Συνάρτηση για να αποθηκεύει υπενθυμίσεις
async def save_reminder(user_id, message, reminder_time, repeat_interval=None):
    conn, cursor = connect_db()
    try:
        logging.info(f"📝 Αποθήκευση υπενθύμισης -> User: {user_id}, Msg: {message}, Time: {reminder_time}, Repeat: {repeat_interval}")

        cursor.execute(
            "INSERT INTO reminders (user_id, message, reminder_time, repeat_interval) VALUES (%s, %s, %s, %s)",
            (user_id, message, reminder_time, repeat_interval)
        )
        conn.commit()
        logging.info("✅ Η υπενθύμιση αποθηκεύτηκε επιτυχώς!")
    except Exception as e:
        logging.error(f"❌ Σφάλμα κατά την αποθήκευση υπενθύμισης: {e}")
    finally:
        cursor.close()
        conn.close()

# Συνάρτηση που ελέγχει και στέλνει υπενθυμίσεις
async def check_reminders():
    while True:
        conn, cursor = connect_db()
        now = datetime.now() + timedelta(hours=0)  # Προσθήκη 0 ωρών για ώρα Ελλάδας
        
        logging.info(f"🔍 Έλεγχος υπενθυμίσεων ({now})")

        cursor.execute("SELECT id, user_id, message, reminder_time, repeat_interval FROM reminders WHERE reminder_time <= %s", (now,))
        reminders = cursor.fetchall()

        for reminder in reminders:
            reminder_id, user_id, message, reminder_time, repeat_interval = reminder

            try:
                await bot.send_message(user_id, f"🔔 Υπενθύμιση: {message}")
                logging.info(f"📨 Στάλθηκε υπενθύμιση: {message}")

                if repeat_interval:
                    next_time = reminder_time + timedelta(seconds=repeat_interval)
                    cursor.execute("UPDATE reminders SET reminder_time = %s WHERE id = %s", (next_time, reminder_id))
                    logging.info(f"🔄 Επαναπρογραμματίστηκε για: {next_time}")
                else:
                    cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
                    logging.info(f"🗑 Διαγράφηκε υπενθύμιση ID {reminder_id}")

                conn.commit()

            except Exception as e:
                logging.error(f"❌ Σφάλμα κατά την αποστολή υπενθύμισης: {e}")

        cursor.close()
        conn.close()
        await asyncio.sleep(60)

# Χειριστής εντολής /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Γεια σου! Στείλε /remind <αριθμός> <μονάδα χρόνου> <μήνυμα> για να αποθηκεύσεις μια υπενθύμιση. Π.χ. /remind 2 ώρες Να πάρω τηλέφωνο.")

# Χειριστής εντολής /list_reminders
@router.message(Command("list_reminders"))
async def list_reminders(message: types.Message):
    conn, cursor = connect_db()
    cursor.execute("SELECT id, message, reminder_time FROM reminders WHERE user_id = %s ORDER BY reminder_time ASC", (message.from_user.id,))
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()

    if not reminders:
        await message.answer("❌ Δεν έχεις αποθηκευμένες υπενθυμίσεις.")
        return

    reminder_text = "\n".join([f"{idx+1}. 📅 {r[2].strftime('%d-%m-%Y %H:%M')} - {r[1]}" for idx, r in enumerate(reminders)])
    await message.answer(f"📌 Οι υπενθυμίσεις σου:\n{reminder_text}")

# Χειριστής εντολής /delete_reminder
@router.message(Command("delete_reminder"))
async def delete_reminder(message: types.Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("❌ Χρήση: /delete_reminder <αριθμός υπενθύμισης>")

        reminder_index = int(args[1]) - 1

        conn, cursor = connect_db()
        cursor.execute("SELECT id FROM reminders WHERE user_id = %s ORDER BY reminder_time ASC", (message.from_user.id,))
        reminders = cursor.fetchall()

        if 0 <= reminder_index < len(reminders):
            reminder_id = reminders[reminder_index][0]
            cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
            conn.commit()
            await message.answer("🗑 Υπενθύμιση διαγράφηκε επιτυχώς!")
        else:
            await message.answer("❌ Μη έγκυρος αριθμός υπενθύμισης.")

        cursor.close()
        conn.close()

    except ValueError as e:
        await message.answer(str(e))

# Εκκίνηση της υπενθύμισης στο παρασκήνιο
async def main():
    dp.include_router(router)
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
