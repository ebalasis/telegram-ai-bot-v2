import os
import logging
import asyncio
import psycopg2
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from datetime import datetime, timedelta
import pytz

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Περιβάλλον
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# Σύνδεση με βάση δεδομένων
def connect_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn, conn.cursor()

# Ζώνη ώρας Ελλάδας
GR_TZ = pytz.timezone("Europe/Athens")

# Αποθήκευση υπενθύμισης
async def save_reminder(user_id, message, reminder_time, repeat_interval=None):
    conn, cursor = connect_db()
    try:
        cursor.execute(
            "INSERT INTO reminders (user_id, message, reminder_time, repeat_interval) VALUES (%s, %s, %s, %s)",
            (user_id, message, reminder_time, repeat_interval)
        )
        conn.commit()
        logging.info(f"✅ Αποθηκεύτηκε: {message} για {reminder_time}")
    except Exception as e:
        logging.error(f"❌ Σφάλμα στην αποθήκευση: {e}")
    finally:
        cursor.close()
        conn.close()

# Έλεγχος και αποστολή υπενθυμίσεων
async def check_reminders():
    while True:
        conn, cursor = connect_db()
        now = datetime.now(GR_TZ)
        cursor.execute("SELECT id, user_id, message, reminder_time, repeat_interval FROM reminders WHERE reminder_time <= %s", (now,))
        reminders = cursor.fetchall()
        
        for reminder_id, user_id, message, reminder_time, repeat_interval in reminders:
            try:
                await bot.send_message(user_id, f"🔔 Υπενθύμιση: {message}")
                logging.info(f"📨 Στάλθηκε υπενθύμιση σε {user_id}: {message}")
                
                if repeat_interval:
                    next_time = reminder_time + timedelta(seconds=repeat_interval)
                    cursor.execute("UPDATE reminders SET reminder_time = %s WHERE id = %s", (next_time, reminder_id))
                else:
                    cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
                conn.commit()
            except Exception as e:
                logging.error(f"❌ Σφάλμα κατά την αποστολή: {e}")
        
        cursor.close()
        conn.close()
        await asyncio.sleep(60)

# Χειριστής εντολής /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Καλώς ήρθες! Χρησιμοποίησε /remind για υπενθυμίσεις.")

# Χειριστής εντολής /remind
@router.message(Command("remind"))
async def remind_command(message: types.Message):
    try:
        args = message.text.split(maxsplit=3)
        if len(args) < 4:
            raise ValueError("❌ Χρήση: /remind <αριθμός> <μονάδα> <μήνυμα>")

        time_value, time_unit, reminder_text = int(args[1]), args[2], args[3]
        units = {"λεπτά": 60, "ώρες": 3600, "μέρες": 86400}
        
        if time_unit not in units:
            raise ValueError("❌ Χρησιμοποίησε λεπτά, ώρες ή μέρες.")
        
        reminder_time = datetime.now(GR_TZ) + timedelta(seconds=time_value * units[time_unit])
        await save_reminder(message.from_user.id, reminder_text, reminder_time)
        await message.answer(f"✅ Αποθηκεύτηκε για {time_value} {time_unit}!")
    except ValueError as e:
        await message.answer(str(e))

# Χειριστής εντολής /list_reminders
@router.message(Command("list_reminders"))
async def list_reminders(message: types.Message):
    conn, cursor = connect_db()
    cursor.execute("SELECT message, reminder_time FROM reminders WHERE user_id = %s ORDER BY reminder_time ASC", (message.from_user.id,))
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not reminders:
        await message.answer("❌ Δεν έχεις υπενθυμίσεις.")
    else:
        reminder_text = "\n".join([f"📅 {r[1].strftime('%d-%m-%Y %H:%M')} - {r[0]}" for r in reminders])
        await message.answer(f"📌 Οι υπενθυμίσεις σου:\n{reminder_text}")

# Εκκίνηση
async def main():
    dp.include_router(router)
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
