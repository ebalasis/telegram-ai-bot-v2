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

# Google Calendar API
SERVICE_ACCOUNT_FILE = "ilias-calendar-api.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
CALENDAR_ID = "ebalasis@yahoo.gr"

def get_calendar_service():
    return build("calendar", "v3", credentials=CREDENTIALS)

# Φόρτωση περιβάλλοντος
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Δημιουργία bot και router
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dp = Dispatcher()

# **Χειριστής εντολής /events (Εμφάνιση επερχόμενων γεγονότων)**
@router.message(Command("events"))
async def list_events(message: types.Message):
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId=CALENDAR_ID, timeMin=now, maxResults=5, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        await message.answer("Δεν υπάρχουν προγραμματισμένα γεγονότα.")
        return

    event_list = "\n".join([f"📅 {event['summary']} στις {event['start'].get('dateTime', event['start'].get('date'))}" for event in events])
    await message.answer(f"📋 Επόμενα γεγονότα:\n{event_list}")

# **Χειριστής εντολής /add_event (Προσθήκη νέου γεγονότος)**
@router.message(Command("add_event"))
async def add_event(message: types.Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise ValueError("❌ Χρήση: /add_event <YYYY-MM-DD HH:MM> <Τίτλος>")
        
        event_time_str = args[1]
        event_title = args[2]
        event_time = datetime.strptime(event_time_str, "%Y-%m-%d %H:%M").isoformat()
        
        event = {
            'summary': event_title,
            'start': {'dateTime': event_time, 'timeZone': 'Europe/Athens'},
            'end': {'dateTime': (datetime.strptime(event_time_str, "%Y-%m-%d %H:%M") + timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Athens'},
        }
        
        service = get_calendar_service()
        event_result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        
        await message.answer(f"✅ Το γεγονός '{event_title}' προστέθηκε για {event_time_str}!")
    except ValueError as e:
        await message.answer(str(e))
    except Exception as e:
        logging.error(f"❌ Σφάλμα προσθήκης γεγονότος: {e}")
        await message.answer("❌ Σφάλμα κατά την προσθήκη του γεγονότος. Βεβαιώσου ότι η ημερομηνία είναι στη σωστή μορφή.")

# **Εκκίνηση του bot**
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
