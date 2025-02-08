import logging
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL

# Configure logger
logger = logging.getLogger('telegram_bot')
logger.setLevel(LOG_LEVEL)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(
    'bot.log',
    maxBytes=1024 * 1024,  # 1MB
    backupCount=5
)

# Create formatters
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set formatters for handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
