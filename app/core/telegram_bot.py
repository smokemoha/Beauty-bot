import datetime
from datetime import timedelta, datetime, time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    JobQueue
)
import logging
import os
import json
# import pytz
from dotenv import load_dotenv
from typing import Dict, Optional
from datetime import datetime, timedelta

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
from core.constants import (
    CHOOSING, BOOKING_SERVICE, BOOKING_DATE, BOOKING_TIME, 
    BOOKING_CONFIRM, SELECTING_LANGUAGE
)

class UserSession:
    def __init__(self, user_id: int, language: str = "en"):
        self.user_id = user_id
        self.language = language
        self.selected_service = None
        self.selected_date = None
        self.selected_time = None
        self.last_interaction = datetime.now()
        self.appointments = []

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "language": self.language,
            "selected_service": self.selected_service,
            "selected_date": self.selected_date.isoformat() if self.selected_date else None,
            "selected_time": self.time_to_str(self.selected_time),
            "last_interaction": self.last_interaction.isoformat(),
            "appointments": self.appointments
        }

    def has_appointment(self, date: datetime.date, time: datetime.time) -> bool:
        """Check if the user has an appointment at the specified date and time."""
        for appointment in self.appointments:
            appointment_date = datetime.fromisoformat(appointment["date"]).date()
            appointment_time = datetime.strptime(appointment["time"], "%H:%M:%S").time()
            if appointment_date == date and appointment_time == time:
                logger.debug(f"Appointment conflict found: {appointment} for user {self.user_id}.")
                return True
        return False

    def delete_appointment(self, user_id: int, service: str, date: str, time: str) -> bool:
        """
        Delete an appointment for a specific user.
        
        Args:
            user_id (int): The user's ID.
            service (str): The name of the service.
            date (str): The date of the appointment (ISO format).
            time (str): The time of the appointment (HH:MM:SS format).
        
        Returns:
            bool: True if the appointment was deleted, False if it wasn't found.
        """
        if user_id not in self.sessions:
            logger.warning(f"User {user_id} not found in sessions.")
            return False

        session = self.sessions[user_id]
        original_count = len(session.appointments)
        session.appointments = [
            appointment for appointment in session.appointments
            if not (
                appointment["service"] == service and
                appointment["date"] == date and
                appointment["time"] == time
            )
        ]

        if len(session.appointments) < original_count:
            self.save_sessions()
            logger.info(f"Deleted appointment for user {user_id}: {service} on {date} at {time}.")
            return True
        else:
            logger.warning(f"No matching appointment found for user {user_id}: {service} on {date} at {time}.")
            return False


    @classmethod
    def from_dict(cls, data: dict) -> 'UserSession':
        session = cls(data["user_id"], data["language"])
        session.selected_service = data["selected_service"]
        session.selected_date = datetime.fromisoformat(data["selected_date"]) if data["selected_date"] else None
        
        # Use str_to_time to parse the 'HH:MM:SS' string back into a time object
        session.selected_time = cls.str_to_time(data["selected_time"])
        session.last_interaction = datetime.fromisoformat(data["last_interaction"])
        session.appointments = data["appointments"]
        return session

    @staticmethod
    def time_to_str(t: Optional[time]) -> Optional[str]:
        """Convert a time object to a 'HH:MM:SS' string."""
        return t.strftime("%H:%M:%S") if t else None

    @staticmethod
    def str_to_time(s: Optional[str]) -> Optional[time]:
        """Convert a 'HH:MM:SS' string to a time object."""
        return datetime.strptime(s, "%H:%M:%S").time() if s else None

class SessionManager:
    def __init__(self, file_path: str = "user_sessions.json"):
        self.file_path = file_path
        self.sessions: Dict[int, UserSession] = {}
        self.load_sessions()

    def get_session(self, user_id: int) -> UserSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]

    def save_sessions(self):
        try:
            with open(self.file_path, 'w') as f:
                json.dump({
                    str(user_id): session.to_dict()
                    for user_id, session in self.sessions.items()
                }, f, indent=4)  # Pretty-print for easier debugging
            logger.info(f"User sessions saved to {self.file_path}.")
        except Exception as e:
            logger.error(f"Failed to save user sessions: {e}")


    # def save_sessions(self):
    #     with open(self.file_path, 'w') as f:
    #         json.dump({
    #             str(user_id): session.to_dict()
    #             for user_id, session in self.sessions.items()
    #         }, f)

    def load_sessions(self):
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                self.sessions = {
                    int(user_id): UserSession.from_dict(session_data)
                    for user_id, session_data in data.items()
                }
        except FileNotFoundError:
            self.sessions = {}

class Translations:
    def __init__(self):
        self.translations = {
            "en": {
                "welcome": "👋 Hi {}! I'm Anna, your personal beauty consultant.",
                "book_service": "📅 Book Service",
                "services": "💄 Services",
                "prices": "💰 Prices",
                "help": "❓ Help",
                "select_service": "Please select a service:",
                "select_date": "Please select a date:",
                "select_time": "Please select a time:",
                "booking_confirmation": "Booking confirmation for {}:\nService: {}\nDate: {}\nTime: {}\n\nConfirm?",
                "booking_confirmed": "Your appointment has been confirmed! See you on {} at {}.",
                "reminder": "Reminder: You have an appointment for {} tomorrow at {}.",
                "check_appointments": "📖 Check Appointments",
                "no_appointments": "You have no appointments.",
                "appointments_list": "Here are your upcoming appointments:\n{}",
                "appointment_conflict": "You already have an appointment on {} at {}. Please choose a different time.",
                "cancel_appointment": "❌ Cancel Appointment",
                "no_appointments_to_cancel": "You have no appointments to cancel.",
                "select_appointment_to_cancel": "Please select the appointment you want to cancel:",
                "appointment_cancelled": "Your appointment for {} on {} at {} has been cancelled.",
                "cancellation_confirmed": "✅ Appointment cancelled."
            },
            "ru": {
                "welcome": "👋 Привет {}! Я Анна, ваш персональный консультант по красоте.",
                "book_service": "📅 Записаться",
                "services": "💄 Услуги",
                "prices": "💰 Цены",
                "help": "❓ Помощь",
                "select_service": "Пожалуйста, выберите услугу:",
                "select_date": "Пожалуйста, выберите дату:",
                "select_time": "Пожалуйста, выберите время:",
                "booking_confirmation": "Подтверждение записи для {}:\nУслуга: {}\nДата: {}\nВремя: {}\n\nПодтвердить?",
                "booking_confirmed": "Ваша запись подтверждена! Ждём вас {} в {}.",
                "reminder": "Напоминание: У вас завтра запись на {} в {}.",
                "check_appointments": "📖 Проверить записи",
                "no_appointments": "У вас нет записей.",
                "appointments_list": "Вот ваши предстоящие записи:\n{}",
                "appointment_conflict": "У вас уже есть запись {} в {}. Пожалуйста, выберите другое время.",
                "cancel_appointment": "❌ Отменить запись",
                "no_appointments_to_cancel": "У вас нет записей для отмены.",
                "select_appointment_to_cancel": "Пожалуйста, выберите запись для отмены:",
                "appointment_cancelled": "Ваша запись на {} {} в {} была отменена.",
                "cancellation_confirmed": "✅ Запись отменена."
            }
        }

    def get(self, key: str, lang: str, *args) -> str:
        translation = self.translations.get(lang, self.translations["en"]).get(key, "")
        return translation.format(*args) if args else translation

class AnnaTelegramBot:
    def __init__(self):
        self.beauty_bot = BeautyServiceBot(api_key=os.getenv("GEMINI_API_KEY"))
        self.session_manager = SessionManager()
        self.translations = Translations()
        
        # Available time slots (in 24-hour format)
        self.time_slots = [
            "09:00", "10:00", "11:00", "12:00", "13:00", 
            "14:00", "15:00", "16:00", "17:00", "18:00"
        ]

    def create_date_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard with available dates (next 7 days)."""
        keyboard = []
        today = datetime.now()
        
        for i in range(7):
            date = today + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            display_str = date.strftime("%A, %b %d")
            keyboard.append([InlineKeyboardButton(display_str, callback_data=f"date_{date_str}")])
            
        return InlineKeyboardMarkup(keyboard)

    async def start_booking_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE, service: str):
        """Start the booking flow for a specific service."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)

        # Set the selected service
        session.selected_service = service

        # Ask for a date
        await update.message.reply_text(
            self.translations.get("select_date", session.language),
            reply_markup=self.create_date_keyboard()
        )


    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.effective_user
        session = self.session_manager.get_session(user.id)
        text = update.message.text
        
        # Compare the user's input with translated menu options.
        # If the user chooses "Book Service" (translated according to language), move to booking service.
        if text == self.translations.get("book_service", session.language):
            # Proceed to service booking flow
            await self.handle_booking_service(update, context)
            return BOOKING_SERVICE
        
        elif text == self.translations.get("services", session.language):
            # Show a list of services or provide more info
            services_list = self.beauty_bot.list_services()
            services_text = "\n".join([f"- {s.title()}" for s in services_list])
            await update.message.reply_text(services_text)
            return CHOOSING
        
        elif text == self.translations.get("prices", session.language):
            # Show price list for services
            prices_text = []
            for s in self.beauty_bot.list_services():
                info = self.beauty_bot.get_service_info(s)
                prices_text.append(f"{s.title()}: {info['price_from']}")
            await update.message.reply_text("\n".join(prices_text))
            return CHOOSING
        
        elif text == self.translations.get("help", session.language):
            # Show help or instructions
            help_text = (
                "Here is how you can use this bot:\n"
                "- Book a service: Choose 'Book Service'\n"
                "- View available services: Choose 'Services'\n"
                "- View prices: Choose 'Prices'\n"
                "- Need help: Choose 'Help'\n\n"
                "You can also ask me any questions related to beauty services."
            )
            await update.message.reply_text(help_text)
            return CHOOSING

        elif text == self.translations.get("check_appointments", session.language):
            await self.check_appointments(update, context)
            return CHOOSING

        elif text == self.translations.get("cancel_appointment", session.language):
            await self.cancel_appointment(update, context)
            return CHOOSING

        else:
            # If it's not one of the menu commands, let's try the LLM for a helpful response.
            response = self.beauty_bot.process_message(text, language=session.language)
            await update.message.reply_text(response["text"])

            # Handle booking action
            if response.get("action") and response["action"]["type"] == "book":
                session.selected_service = response["action"]["service"]
                await self.start_booking_flow(update, context, session.selected_service)
                return BOOKING_DATE
            return CHOOSING

    async def cancel_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle appointment cancellation."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)

        if not session.appointments:
            await update.message.reply_text(
                self.translations.get("no_appointments_to_cancel", session.language)
            )
            return CHOOSING

        # Generate a list of appointments for selection
        keyboard = []
        for i, appointment in enumerate(session.appointments):
            keyboard.append([
                InlineKeyboardButton(
                    f"{appointment['service']} on {appointment['date']} at {appointment['time']}",
                    callback_data=f"cancel_{i}"
                )
            ])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            self.translations.get("select_appointment_to_cancel", session.language),
            reply_markup=reply_markup
        )
        return CHOOSING



    async def check_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle checking of appointments."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)

        if not session.appointments:
            await update.message.reply_text(
                self.translations.get("no_appointments", session.language)
            )
        else:
            appointments = "\n".join([
                f"- {a['service']} on {a['date']} at {a['time']}"
                for a in session.appointments
            ])
            await update.message.reply_text(
                self.translations.get("appointments_list", session.language, appointments)
            )

        return CHOOSING

    def create_time_keyboard(self, date_str: str) -> InlineKeyboardMarkup:
        """Create keyboard with available time slots."""
        keyboard = []
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # If it's today, only show future time slots
        if selected_date == datetime.now().date():
            current_hour = datetime.now().hour
            available_slots = [slot for slot in self.time_slots 
                                if int(slot.split(":")[0]) > current_hour]
        else:
            available_slots = self.time_slots

        # Create rows of 3 time slots each
        row = []
        for slot in available_slots:
            row.append(InlineKeyboardButton(slot, callback_data=f"time_{slot}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        if row:  # Add any remaining slots
            keyboard.append(row)
            
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send welcome message and initialize user session."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)
        
        # Language selection keyboard
        keyboard = [
            [KeyboardButton("🇺🇸 English"), KeyboardButton("🇷🇺 Русский")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Please select your language / Пожалуйста, выберите язык:",
            reply_markup=reply_markup
        )
        
        return SELECTING_LANGUAGE

    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Set user's preferred language."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)
        
        if "English" in update.message.text:
            session.language = "en"
        else:
            session.language = "ru"
        
        self.session_manager.save_sessions()
        
        # Create main menu keyboard
        keyboard = [
            [KeyboardButton(self.translations.get("book_service", session.language)),
                KeyboardButton(self.translations.get("services", session.language))],
            [KeyboardButton(self.translations.get("prices", session.language)),
                KeyboardButton(self.translations.get("help", session.language))],
            [KeyboardButton(self.translations.get("check_appointments", session.language))],
            [KeyboardButton(self.translations.get("cancel_appointment", session.language))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            self.translations.get("welcome", session.language, user.first_name),
            reply_markup=reply_markup
        )
        
        return CHOOSING

    async def cancel(self, update:  Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.effective_user
        session = self.session_manager.get_session(user.id)
        await update.message.reply_text("Conversation cancelled.")
        return ConversationHandler.END


    async def suggest_time_slots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Suggest time slots for the selected date."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)

        # Create time slot buttons
        reply_markup = self.create_time_keyboard(session.selected_date.strftime("%Y-%m-%d"))

        # Use callback_query if available, otherwise use message
        if update.callback_query:
            await update.callback_query.message.reply_text(
                self.translations.get("select_time", session.language),
                reply_markup=reply_markup
            )
        elif update.message:
            await update.message.reply_text(
                self.translations.get("select_time", session.language),
                reply_markup=reply_markup
            )


    async def handle_booking_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle service selection for booking."""
        user = update.effective_user
        session = self.session_manager.get_session(user.id)
        
        keyboard = []
        for service in self.beauty_bot.list_services():
            info = self.beauty_bot.get_service_info(service)
            display_text = f"{service.title()} ({info['price_from']})"
            keyboard.append([InlineKeyboardButton(display_text, callback_data=f"service_{service}")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            self.translations.get("select_service", session.language),
            reply_markup=reply_markup
        )
        
        return BOOKING_SERVICE

    async def handle_booking_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle callback queries from inline keyboards during booking."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        session = self.session_manager.get_session(user.id)
        
        data = query.data
        
        if data.startswith("service_"):
            session.selected_service = data.replace("service_", "")
            await query.edit_message_text(
                text=self.translations.get("select_date", session.language),
                reply_markup=self.create_date_keyboard()
            )
            return BOOKING_DATE
            
        elif data.startswith("date_"):
            session.selected_date = datetime.strptime(data.replace("date_", ""), "%Y-%m-%d")
            await self.suggest_time_slots(update, context)
            return BOOKING_TIME

        elif data.startswith("time_"):
                selected_time = datetime.strptime(data.replace("time_", ""), "%H:%M").time()
                session.selected_time = selected_time

                # Check for conflicting appointments
                if session.has_appointment(session.selected_date, selected_time):
                    await query.edit_message_text(
                        text=self.translations.get(
                            "appointment_conflict",
                            session.language,
                            session.selected_date.strftime("%Y-%m-%d"),
                            selected_time.strftime("%H:%M")
                        )
                    )
                    logger.info(f"Double booking prevented for user {session.user_id} on {session.selected_date} at {selected_time}.")
                    return BOOKING_TIME

                # Proceed to confirmation
                confirmation_text = self.translations.get(
                    "booking_confirmation",
                    session.language,
                    user.first_name,
                    session.selected_service,
                    session.selected_date.strftime("%Y-%m-%d"),
                    session.selected_time.strftime("%H:%M")
                )
                
                keyboard = [
                    [InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
                    InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")]
                ]
                await query.edit_message_text(
                    text=confirmation_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return BOOKING_CONFIRM

            
        elif data.startswith("confirm_"):
            if data == "confirm_yes":
                if session.has_appointment(session.selected_date, session.selected_time):
                    await query.edit_message_text(
                        text=self.translations.get(
                            "appointment_conflict",
                            session.language,
                            session.selected_date.strftime("%Y-%m-%d"),
                            session.selected_time.strftime("%H:%M")
                        )
                    )
                    logger.warning(f"Duplicate appointment detected during confirmation for user {session.user_id}.")
                    return BOOKING_TIME

                # Save appointment
                appointment = {
                    "service": session.selected_service,
                    "date": session.selected_date.isoformat(),
                    # "time": session.selected_time.isoformat()
                    "time": UserSession.time_to_str(session.selected_time)
                }
                session.appointments.append(appointment)
                self.session_manager.save_sessions()
                
                # Schedule reminder
                appointment_datetime = datetime.combine(session.selected_date, session.selected_time)
                reminder_time = appointment_datetime - timedelta(days=1)
                
                context.application.job_queue.run_once(
                    self.send_reminder,
                    reminder_time,
                    data={
                        "user_id": user.id,
                        "service": session.selected_service,
                        "time": session.selected_time.strftime("%H:%M")
                    }
                )
                
                await query.edit_message_text(
                    text=self.translations.get(
                        "booking_confirmed",
                        session.language,
                        session.selected_date.strftime("%Y-%m-%d"),
                        session.selected_time.strftime("%H:%M")
                    )
                )

            elif data.startswith("cancel_"):
                index = int(data.replace("cancel_", ""))
                if 0 <= index < len(session.appointments):
                    appointment = session.appointments[index]

                    # Call the delete_appointment method
                    success = self.session_manager.delete_appointment(
                        user_id=session.user_id,
                        service=appointment["service"],
                        date=appointment["date"],
                        time=appointment["time"]
                    )

                    if success:
                        await query.edit_message_text(
                            text=self.translations.get(
                                "appointment_cancelled",
                                session.language,
                                appointment["service"],
                                appointment["date"],
                                appointment["time"]
                            )
                        )
                    else:
                        await query.edit_message_text(
                            text="Failed to cancel the appointment. Please try again."
                        )
                else:
                    await query.edit_message_text(
                        text="Invalid appointment selected for cancellation."
                    )

                return CHOOSING
            
            else:
                await query.edit_message_text("Booking cancelled. How else can I help you?")
            
            # Reset booking data
            session.selected_service = None
            session.selected_date = None
            session.selected_time = None
            
            return CHOOSING

    async def send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Send appointment reminder."""
        job = context.job
        user_id = job.data["user_id"]
        session = self.session_manager.get_session(user_id)
        
        reminder_text = self.translations.get(
            "reminder",
            session.language,
            job.data["service"],
            job.data["time"]
        )
        
        await context.bot.send_message(user_id, reminder_text)

    def run(self):
        """Run the bot."""
        application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
        application.job_queue.start()

        # Add conversation handler with the new states
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                SELECTING_LANGUAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_language)
                ],
                CHOOSING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
                ],
                BOOKING_DATE: [
                    CallbackQueryHandler(self.handle_booking_callback)
                ],
                BOOKING_TIME: [
                    CallbackQueryHandler(self.handle_booking_callback)
                ],
                BOOKING_CONFIRM: [
                    CallbackQueryHandler(self.handle_booking_callback)
                ],
                BOOKING_SERVICE: [
                    CallbackQueryHandler(self.handle_booking_callback)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        application.add_handler(conv_handler)
        application.run_polling()
