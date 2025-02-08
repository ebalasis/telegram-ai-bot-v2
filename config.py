import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Greek messages
MESSAGES = {
    'welcome': 'Καλώς ήρθατε! Είμαι ένα bot που επαναλαμβάνει τα μηνύματά σας.',
    'echo_prefix': 'Είπατε: ',
    'error': 'Συγγνώμη, προέκυψε ένα σφάλμα. Παρακαλώ δοκιμάστε ξανά.',
}

# Database connection
DATABASE_URL = os.getenv("postgresql://postgres:jitvcjHcHnWKoMVDMXGPcJhFdukRjukO@roundhouse.proxy.rlwy.net:51799/railway")
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables")

try:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    
    # Create table for reminders if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    print("✅ Database Connected & Table Created!")
except Exception as e:
    print(f"❌ Database connection error: {e}")
