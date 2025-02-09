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
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from google.oauth2 import service_account

# Telegram ID χρήστη για ειδοποιήσεις
TELEGRAM_USER_ID = 5375897237  

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Ζώνη ώρας Ελλάδας
GR_TZ = timezone('Europe/Athens')

def get_greek_time_minus_one_hour():
    return datetime.now(GR_TZ) - timedelta(hours=1)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GMAIL_API_CREDENTIALS_JSON = os.getenv("GMAIL_API_CREDENTIALS_JSON")

# Μετατροπή του JSON string σε dict
google_creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
gmail_creds_dict = json.loads(GMAIL_API_CREDENTIALS_JSON)

# Δημιουργία credentials από dict
google_credentials = service_account.Credentials.from_service_account_info(google_creds_dict, scopes=['https://www.googleapis.com/auth/calendar'])
gmail_credentials = service_account.Credentials.from_service_account_info(gmail_creds_dict, scopes=['https://www.googleapis.com/auth/gmail.readonly'])
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# Google Calendar API Setup
import json

def get_calendar_service():
    credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')

    if not credentials_json:
        logging.error("❌ GOOGLE_CREDENTIALS δεν έχει οριστεί στο περιβάλλον.")
        return None

    try:
        creds_info = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logging.error(f"❌ Σφάλμα κατά τη φόρτωση των credentials: {e}")
        return None


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
        await bot.send_message(user_id, f"✅ Η υπενθύμιση σου αποθηκεύτηκε: {message} για {reminder_time.strftime('%d-%m-%Y %H:%M')}")
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
    await message.answer("👋 Γεια σου! Το bot είναι έτοιμο. Χρησιμοποίησε τις διαθέσιμες εντολές για να διαχειριστείς τις υπενθυμίσεις και το ημερολόγιό σου.")

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

        TIME_UNITS = {"λεπτό": 60, "λεπτά": 60, "ώρα": 3600, "ώρες": 3600}
        seconds = int(time_value) * TIME_UNITS.get(time_unit, 0)
        if seconds == 0:
            raise ValueError("❌ Μη έγκυρη μονάδα χρόνου.")

        reminder_time = get_greek_time_minus_one_hour() + timedelta(seconds=seconds)
        await save_reminder(message.from_user.id, reminder_text, reminder_time)
    except ValueError as e:
        await message.answer(str(e))

# **Χειριστής εντολής /list_events**
@router.message(Command("list_events"))
async def list_events(message: types.Message):
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now, maxResults=5, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        await message.answer("❌ Δεν υπάρχουν προγραμματισμένα γεγονότα.")
        return

    event_list = "\n".join([f"📅 {event['start'].get('dateTime', event['start'].get('date'))} - {event['summary']}" for event in events])
    await message.answer(f"📆 Επόμενα γεγονότα:\n{event_list}")

# **Χειριστής εντολής /add_event**
@router.message(Command("add_event"))
async def add_event(message: types.Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise ValueError("❌ Χρήση: /add_event <YYYY-MM-DD HH:MM> <Τίτλος γεγονότος>")

        event_time = datetime.strptime(args[1], "%Y-%m-%d %H:%M")
        event_title = args[2]

        event = {
            'summary': event_title,
            'start': {'dateTime': event_time.isoformat(), 'timeZone': 'Europe/Athens'},
            'end': {'dateTime': (event_time + timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Athens'}
        }

        service = get_calendar_service()
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        await message.answer(f"✅ Το γεγονός '{event_title}' προστέθηκε στο ημερολόγιο!")
        await bot.send_message(TELEGRAM_USER_ID, f"📅 Προστέθηκε νέο γεγονός: {event_title} στις {args[1]}")
    except Exception as e:
        await message.answer(f"❌ Σφάλμα: {str(e)}")

# **Εκκίνηση του bot**
async def main():
    dp.include_router(router)
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
