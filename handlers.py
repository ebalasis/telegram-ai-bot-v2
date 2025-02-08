import telebot
from config import MESSAGES
from logger import logger

def register_handlers(bot: telebot.TeleBot):
    """Register all message handlers"""
    
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        """Handle /start command"""
        try:
            logger.info(f"Received /start command from user {message.from_user.id}")
            bot.reply_to(message, MESSAGES['welcome'])
        except Exception as e:
            logger.error(f"Error in start handler: {str(e)}")
            bot.reply_to(message, MESSAGES['error'])

    @bot.message_handler(func=lambda message: True)
    def echo_message(message):
        """Echo all messages back to user"""
        try:
            logger.info(f"Received message from user {message.from_user.id}: {message.text}")
            response = f"{MESSAGES['echo_prefix']}{message.text}"
            bot.reply_to(message, response)
        except Exception as e:
            logger.error(f"Error in echo handler: {str(e)}")
            bot.reply_to(message, MESSAGES['error'])
