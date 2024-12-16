
from dotenv import load_dotenv
from typing import Dict
import asyncio

from core.telegram_bot import AnnaTelegramBot

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    bot = AnnaTelegramBot()
    
    bot.run()