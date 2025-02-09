import os
import logging
import asyncio
import json
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

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Ζώνη ώρας Ελλάδας
GR_TZ = timezone('Europe/Athens')
def get_greek_time_minus_one_hour():
    return datetime.now(GR_TZ) - timedelta(hours=1)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')

# Ρύθμιση του Google Calendar API
if not GOOGLE_CREDENTIALS:
    raise ValueError("❌ Δεν βρέθηκε η μεταβλητή GOOGLE_CREDENTIALS. Βεβαιώσου ότι την πρόσθεσες στο Railway!")
credentials_info = json.loads(GOOGLE_CREDENTIALS)
SCOPES = ["https://www.googleapis.com/auth/calendar"]
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
service = build("calendar", "v3", credentials=credentials)
CALENDAR_ID = "ebalasis@yahoo.gr"  # Βεβαιώσου ότι είναι σωστό το email του ημερολογίου σου

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# **Χειριστής εντολής /events (Προβολή επόμενων γεγονότων)**
@router.message(Command("events"))
async def list_calendar_events(message: types.Message):
    now = datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now, maxResults=5, singleEvents=True, orderBy="startTime").execute()
    events = events_result.get("items", [])
    if not events:
        await message.answer("📅 Δεν υπάρχουν προγραμματισμένα γεγονότα.")
        return
    event_list = "\n".join([f"📌 {event['summary']} - {event['start'].get('dateTime', event['start'].get('date'))}" for event in events])
    await message.answer(f"📆 Επόμενα γεγονότα:\n{event_list}")

# **Χειριστής εντολής /add_event (Προσθήκη νέου γεγονότος)**
@router.message(Command("add_event"))
async def add_calendar_event(message: types.Message):
    try:
        args = message.text.split(maxsplit=4)
        if len(args) < 5:
            await message.answer("❌ Χρήση: /add_event <Ημερομηνία YYYY-MM-DD> <Ώρα HH:MM> <Διάρκεια σε λεπτά> <Τίτλος>")
            return
        date, time, duration, summary = args[1], args[2], int(args[3]), args[4]
        start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(minutes=duration)
        event = {
            "summary": summary,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Europe/Athens"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "Europe/Athens"},
        }
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        await message.answer(f"✅ Προστέθηκε το γεγονός: {summary} στις {date} {time}!")
    except Exception as e:
        await message.answer(f"❌ Σφάλμα: {e}")

# **Εκκίνηση της υπενθύμισης στο παρασκήνιο**
async def main():
    dp.include_router(router)
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
