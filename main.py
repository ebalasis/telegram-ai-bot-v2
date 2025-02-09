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

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Ζώνη ώρας Ελλάδας
GR_TZ = timezone('Europe/Athens')
def get_greek_time_minus_one_hour():
    return datetime.now(GR_TZ) - timedelta(hours=1)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
CALENDAR_ID = os.getenv('CALENDAR_ID')  # Βάλε το ID του ημερολογίου σου
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# Google Calendar API Setup
def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=creds)

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
    except Exception as e:
        await message.answer(f"❌ Σφάλμα: {str(e)}")

# **Εκκίνηση της υπενθύμισης στο παρασκήνιο**
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
