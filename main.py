import telebot
from flask import Flask
import threading

BOT_TOKEN = "7917668963:AAEx1lpoDKbuaeEqB7nKxOFEO_DkMpORwOc"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Γεια σου Ιλία! Είμαι έτοιμος να σε βοηθήσω.")

# Εκκίνηση του bot σε ξεχωριστό thread
def run_bot():
    bot.polling()

bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

# Δημιουργία του Flask web server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Εκκίνηση του Flask web server σε ξεχωριστό thread
flask_thread = threading.Thread(target=run)
flask_thread.start()


