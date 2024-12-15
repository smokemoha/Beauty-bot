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

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
CHOOSING, BOOKING = range(2)

class AnnaTelegramBot:
    def __init__(self):
        # Initialize the beauty service bot
        self.beauty_bot = BeautyServiceBot(openai_api_key=os.getenv("OPENAI_API_KEY"))
        
        # Store active conversations
        self.active_conversations: Dict[int, Dict] = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send welcome message when the command /start is issued."""
        user = update.effective_user
        
        # Create keyboard with main options
        keyboard = [
            [KeyboardButton("📅 Book Service"), KeyboardButton("💄 Services")],
            [KeyboardButton("💰 Prices"), KeyboardButton("❓ Help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_message = (
            f"👋 Hi {user.first_name}! I'm Anna, your personal beauty consultant.\n\n"
            "I can help you with:\n"
            "• Booking beauty services\n"
            "• Information about our services\n"
            "• Prices and availability\n"
            "• Beauty advice and consultations\n\n"
            "How can I assist you today?"
        )
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        return CHOOSING

    async def show_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Display available services."""
        services = self.beauty_bot.list_services()
        
        services_message = "Here are our available services:\n\n"
        for service in services:
            info = self.beauty_bot.get_service_info(service)
            services_message += (
                f"• {service.title()}\n"
                f"  Price: ${info['price']}\n"
                f"  Duration: {info['duration']}\n\n"
            )
        
        await update.message.reply_text(services_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle incoming messages and generate responses using the beauty bot."""
        user_id = update.effective_user.id
        message_text = update.message.text

        # Process specific commands
        if message_text == "💄 Services":
            await self.show_services(update, context)
            return CHOOSING
            
        elif message_text == "📅 Book Service":
            await update.message.reply_text(
                "Which service would you like to book? Please type the service name."
            )
            return BOOKING
            
        elif message_text == "💰 Prices":
            services = self.beauty_bot.list_services()
            price_list = "Our Price List:\n\n"
            for service in services:
                info = self.beauty_bot.get_service_info(service)
                price_list += f"• {service.title()}: ${info['price']}\n"
            await update.message.reply_text(price_list)
            return CHOOSING
            
        elif message_text == "❓ Help":
            help_text = (
                "Here's how I can help you:\n\n"
                "• View services: Click '💄 Services'\n"
                "• Book appointment: Click '📅 Book Service'\n"
                "• Check prices: Click '💰 Prices'\n"
                "• Ask questions: Just type your question\n\n"
                "Need to start over? Type /start"
            )
            await update.message.reply_text(help_text)
            return CHOOSING

        # Process general messages through the beauty bot
        response = self.beauty_bot.process_message(message_text)
        await update.message.reply_text(response)
        return CHOOSING

    async def handle_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the booking process."""
        service_name = update.message.text.lower()
        
        if service_name in self.beauty_bot.services:
            service_info = self.beauty_bot.get_service_info(service_name)
            booking_message = (
                f"Great choice! For {service_name}, here are the details:\n\n"
                f"• Duration: {service_info['duration']}\n"
                f"• Price: ${service_info['price']}\n\n"
                "Please provide your preferred date and time (e.g., 'Tomorrow at 2 PM')"
            )
            await update.message.reply_text(booking_message)
        else:
            await update.message.reply_text(
                "I don't recognize that service. Please choose from our available services:"
            )
            await self.show_services(update, context)
        
        return CHOOSING

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Error occurred: {context.error}")
        await update.message.reply_text(
            "I apologize, but something went wrong. Please try again or contact support."
        )

    def run(self):
        """Run the bot."""
        # Create application
        application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

        # Add conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                CHOOSING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
                ],
                BOOKING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_booking)
                ]
            },
            fallbacks=[CommandHandler('start', self.start)]
        )

        application.add_handler(conv_handler)
        
        # Add error handler
        application.add_error_handler(self.error_handler)
