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
from pytz import timezone

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)


# Ζώνη ώρας Ελλάδας
GR_TZ = timezone('Europe/Athens')
def get_greek_time_minus_one_hour():
    return datetime.now(GR_TZ) - timedelta(hours=1)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# **Συνάρτηση για αποθήκευση υπενθυμίσεων**
async def save_reminder(user_id, message, reminder_time, repeat_interval=None):
    conn, cursor = connect_db()
    try:
        cursor.execute(
            "INSERT INTO reminders (user_id, message, reminder_time, repeat_interval) VALUES (%s, %s, %s, %s)",
            (user_id, message, reminder_time, repeat_interval)
        )
        conn.commit()
        logging.info(f"✅ Υπενθύμιση αποθηκεύτηκε: {message} για {reminder_time} (Επανάληψη: {repeat_interval})")
    except Exception as e:
        logging.error(f"❌ Σφάλμα στην αποθήκευση υπενθύμισης: {e}")
    finally:
        cursor.close()
        conn.close()

# **Συνάρτηση που ελέγχει και στέλνει υπενθυμίσεις**
async def check_reminders():
    while True:
        conn, cursor = connect_db()
        now = get_greek_time_minus_one_hour()

        cursor.execute("SELECT id, user_id, message, reminder_time, repeat_interval FROM reminders WHERE reminder_time <= %s", (now,))
        reminders = cursor.fetchall()

        for reminder in reminders:
            reminder_id, user_id, message, reminder_time, repeat_interval = reminder
            try:
                await bot.send_message(user_id, f"🔔 Υπενθύμιση: {message}")
                if repeat_interval:
                    next_time = reminder_time + timedelta(seconds=repeat_interval)
                    cursor.execute("UPDATE reminders SET reminder_time = %s WHERE id = %s", (next_time, reminder_id))
                else:
                    cursor.execute("DELETE FROM reminders WHERE id = %s", (reminder_id,))
                conn.commit()
            except Exception as e:
                logging.error(f"❌ Σφάλμα κατά την αποστολή υπενθύμισης: {e}")

        cursor.close()
        conn.close()
        await asyncio.sleep(60)

# **Χειριστής εντολής /start**
@router.message(Command("start"))
async def start_command(message: types.Message):
    logging.info(f"📩 Λήφθηκε το /start από τον χρήστη {message.from_user.id}")
    await message.answer("👋 Γεια σου! Στείλε /remind <αριθμός> <μονάδα χρόνου> <μήνυμα> για να αποθηκεύσεις μια υπενθύμιση. Π.χ. /remind 2 ώρες Να πάρω τηλέφωνο.")

# **Συνάρτηση για μετατροπή χρόνου**
TIME_UNITS = {
    "λεπτό": 60, "λεπτά": 60,
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

# **Χειριστής εντολής /remind**
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

        reminder_time = get_greek_time_minus_one_hour() + timedelta(seconds=seconds)
        await save_reminder(message.from_user.id, reminder_text, reminder_time)
        await message.answer(f"✅ Υπενθύμιση αποθηκεύτηκε! Θα λάβεις το μήνυμα σε {time_value} {time_unit}.")

    except ValueError as e:
        await message.answer(str(e))

# **Χειριστής εντολής /list_reminders**
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

    reminder_text = "\n".join([f"📌 ID {r[0]} | 🕒 {r[2].strftime('%d-%m-%Y %H:%M')} - {r[1]}" for r in reminders])
    await message.answer(f"📋 Οι υπενθυμίσεις σου:\n{reminder_text}")

# **Χειριστής εντολής /delete_reminder ID**
@router.message(Command("delete_reminder"))
async def delete_reminder(message: types.Message):
    try:
        reminder_id = int(message.text.split()[1])
        conn, cursor = connect_db()
        cursor.execute("DELETE FROM reminders WHERE id = %s AND user_id = %s", (reminder_id, message.from_user.id))
        conn.commit()
        cursor.close()
        conn.close()
        await message.answer(f"🗑 Η υπενθύμιση με ID {reminder_id} διαγράφηκε.")
    except:
        await message.answer("❌ Χρήση: /delete_reminder <ID>")

# **Χειριστής εντολής /delete_all_reminders**
@router.message(Command("delete_all_reminders"))
async def delete_all_reminders(message: types.Message):
    conn, cursor = connect_db()
    cursor.execute("DELETE FROM reminders WHERE user_id = %s", (message.from_user.id,))
    conn.commit()
    cursor.close()
    conn.close()
    await message.answer("🗑 Όλες οι υπενθυμίσεις διαγράφηκαν!")

# **Εκκίνηση της υπενθύμισης στο παρασκήνιο**
async def main():
    dp.include_router(router)
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
