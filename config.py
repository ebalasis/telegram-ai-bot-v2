import os
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