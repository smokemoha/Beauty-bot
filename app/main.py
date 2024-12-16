from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
import logging
import os
from dotenv import load_dotenv
from typing import Dict

# Import our beauty service bot
from core.chatbot import BeautyServiceBot
from core.telegram_bot import AnnaTelegramBot

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    bot = AnnaTelegramBot()
    bot.run()