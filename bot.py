from database import (
    init_database, 
    save_user, 
    get_user, 
    update_daily_hadith_settings,
    get_all_daily_hadith_users,
)
from dotenv import load_dotenv
import os
import requests
import random
import logging
from datetime import time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HADITH_API_KEY = os.getenv('HADITH_API_KEY')
HADITH_API_BASE = "https://hadithapi.com/api"

WAITING_FOR_TIME = 1

BOOKS = [
    "sahih-bukhari",
    "sahih-muslim",
    "al-tirmidhi",
    "abu-dawood",
    "ibn-e-majah",
    "sunan-nasai"
]

def fetch_random_hadith():
    """Fetch a random hadith from the API"""
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            book = random.choice(BOOKS)
            
            url = f"{HADITH_API_BASE}/hadiths?apiKey={HADITH_API_KEY}&book={book}&paginate=50"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 404:
                logger.warning(f"Book '{book}' returned 404, trying another book...")
                attempt += 1
                continue
                
            response.raise_for_status()
            
            data = response.json()
            
            if 'hadiths' in data and 'data' in data['hadiths'] and len(data['hadiths']['data']) > 0:
                hadith = random.choice(data['hadiths']['data'])
                logger.info(f"Successfully fetched hadith from {book}")
                return hadith
            else:
                logger.warning(f"No hadiths found in {book}, trying another book...")
                attempt += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching hadith (attempt {attempt + 1}/{max_attempts}): {e}")
            attempt += 1
        except Exception as e:
            logger.error(f"Error fetching hadith (attempt {attempt + 1}/{max_attempts}): {e}")
            attempt += 1
    
    logger.error("Failed to fetch hadith after all attempts")
    return None

def format_hadith_message(hadith):
    """Format hadith data into a readable message"""
    if not hadith:
        return "❌ Could not fetch hadith. Please try again."
    
    english = hadith.get('hadithEnglish', 'N/A')
    arabic = hadith.get('hadithArabic', '')
    book_name = hadith.get('book', {}).get('bookName', 'Unknown')
    hadith_number = hadith.get('hadithNumber', 'N/A')
    chapter = hadith.get('chapter', {}).get('chapterEnglish', 'N/A')
    
    message = f"📖 *{book_name}*\n"
    message += f"📚 Hadith #{hadith_number}\n"
    message += f"📑 Chapter: {chapter}\n\n"
    
    if arabic:
        message += f"🔤 *Arabic:*\n{arabic}\n\n"
    
    message += f"🇬🇧 *English:*\n{english}"
    
    return message

def get_main_menu_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📿 Get Random Hadith", callback_data='get_hadith')],
        [InlineKeyboardButton("⏰ Daily Hadith Settings", callback_data='daily_settings')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_daily_settings_keyboard(is_enabled=False):
    """Create daily hadith settings keyboard"""
    if is_enabled:
        keyboard = [
            [InlineKeyboardButton("⏰ Change Time", callback_data='set_time')],
            [InlineKeyboardButton("🔕 Disable Daily Hadith", callback_data='disable_daily')],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("✅ Enable Daily Hadith", callback_data='set_time')],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]
        ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.message.from_user
    
    save_user(
        user_id=user.id,
        chat_id=update.message.chat_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_message = (
        "السلام عليكم ورحمة الله وبركاته\n\n"
        "Welcome to the Hadith Bot! 🕌\n\n"
        "📿 Get random hadiths from authentic collections\n"
        "⏰ Set up daily hadith reminders\n\n"
        "Choose an option below:"
    )
    
    await update.message.reply_text(
        welcome_message, 
        reply_markup=get_main_menu_keyboard()
    )

async def send_daily_hadith(context: ContextTypes.DEFAULT_TYPE):
    """Send daily hadith to user"""
    job = context.job
    chat_id = job.chat_id
    
    hadith = fetch_random_hadith()
    message = format_hadith_message(hadith)
    
    message = "🌅 *Daily Hadith*\n\n" + message
    
    keyboard = [
        [InlineKeyboardButton("🔄 Get Another", callback_data='get_hadith')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='daily_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info(f"Daily hadith sent to chat_id: {chat_id}")
    except Exception as e:
        logger.error(f"Error sending daily hadith to {chat_id}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'get_hadith':
        await query.edit_message_text("⏳ Fetching hadith...")
        
        hadith = fetch_random_hadith()
        message = format_hadith_message(hadith)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Get Another Hadith", callback_data='get_hadith')],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == 'main_menu':
        welcome_message = (
            "السلام عليكم ورحمة الله وبركاته\n\n"
            "Welcome to the Hadith Bot! 🕌\n\n"
            "📿 Get random hadiths from authentic collections\n"
            "⏰ Set up daily hadith reminders\n\n"
            "Choose an option below:"
        )
        await query.edit_message_text(
            welcome_message,
            reply_markup=get_main_menu_keyboard()
        )
    
    elif query.data == 'daily_settings':
        user_id = query.from_user.id
        user_data = get_user(user_id)
        
        is_enabled = user_data and user_data.get('daily_hadith_enabled', False)
        
        if is_enabled:
            time_obj = user_data.get('daily_hadith_time')
            
            if isinstance(time_obj, str):
                time_str = time_obj
            elif hasattr(time_obj, 'hour') and hasattr(time_obj, 'minute'):
                time_str = f"{time_obj.hour:02d}:{time_obj.minute:02d}"
            else:
                total_seconds = int(time_obj.total_seconds())
                hour = total_seconds // 3600
                minute = (total_seconds % 3600) // 60
                time_str = f"{hour:02d}:{minute:02d}"
            
            timezone_str = user_data.get('timezone', 'Europe/Rome')
            
            message = (
                "⏰ *Daily Hadith Settings*\n\n"
                f"✅ Status: Enabled\n"
                f"🕐 Time: {time_str}\n"
                f"🌍 Timezone: {timezone_str}\n\n"
                "You will receive a hadith every day at your set time."
            )
        else:
            message = (
                "⏰ *Daily Hadith Settings*\n\n"
                "❌ Status: Disabled\n\n"
                "Enable daily hadiths to receive a hadith at the same time every day."
            )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_daily_settings_keyboard(is_enabled)
        )
    
    elif query.data == 'set_time':
        await query.edit_message_text(
            "⏰ *Set Daily Hadith Time*\n\n"
            "Please send me the time you want to receive your daily hadith.\n\n"
            "Format: HH:MM (24-hour format)\n"
            "Example: 08:00 or 20:30\n\n"
            "Send /cancel to go back.",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_time'] = True
        return WAITING_FOR_TIME
    
    elif query.data == 'disable_daily':
        user_id = query.from_user.id
        
        update_daily_hadith_settings(user_id, enabled=False, time_str=None)
        
        jobs = context.job_queue.get_jobs_by_name(f"daily_hadith_{user_id}")
        for job in jobs:
            job.schedule_removal()
        
        await query.edit_message_text(
            "✅ Daily hadith has been disabled.\n\n"
            "You can enable it again anytime from the settings.",
            reply_markup=get_daily_settings_keyboard(False)
        )
    
    elif query.data == 'help':
        help_message = (
            "ℹ️ *Hadith Bot Help*\n\n"
            "*Commands:*\n"
            "/start - Show main menu\n"
            "/hadith - Get a random hadith\n"
            "/daily - Daily hadith settings\n"
            "/cancel - Cancel current operation\n\n"
            "*Features:*\n"
            "📿 Random hadiths from 9 authentic collections\n"
            "⏰ Daily hadith reminders at your chosen time\n"
            "🔤 Arabic text with English translation\n\n"
            "*Collections:*\n"
            "• Sahih Bukhari\n"
            "• Sahih Muslim\n"
            "• Jami' Al-Tirmidhi\n"
            "• Sunan Abu Dawood\n"
            "• Sunan Ibn-e-Majah\n"
            "• Sunan An-Nasa'i\n"
            "• Mishkat Al-Masabih\n"
            "• Musnad Ahmad\n"
            "• Al-Silsila Sahiha"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await query.edit_message_text(
            help_message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle time input for daily hadith"""
    if not context.user_data.get('awaiting_time'):
        return
    
    time_text = update.message.text.strip()
    
    try:
        hour, minute = map(int, time_text.split(':'))
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time range")
        
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        
        user_data = get_user(user_id)
        user_timezone_str = user_data.get('timezone', 'Europe/Rome') if user_data else 'Europe/Rome'
        user_timezone = pytz.timezone(user_timezone_str)
        
        update_daily_hadith_settings(user_id, enabled=True, time_str=time_text)
        
        jobs = context.job_queue.get_jobs_by_name(f"daily_hadith_{user_id}")
        for job in jobs:
            job.schedule_removal()
        
        context.job_queue.run_daily(
            send_daily_hadith,
            time=time(hour=hour, minute=minute, tzinfo=user_timezone),
            chat_id=chat_id,
            name=f"daily_hadith_{user_id}",
            user_id=user_id
        )
        
        context.user_data['awaiting_time'] = False
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Settings", callback_data='daily_settings')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        
        await update.message.reply_text(
            f"✅ Daily hadith enabled!\n\n"
            f"You will receive a hadith every day at {time_text}.\n"
            f"🌍 Timezone: {user_timezone_str}\n\n"
            f"Make sure to keep the bot unblocked to receive messages.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(
            "❌ Invalid time format.\n\n"
            "Please use HH:MM format (24-hour).\n"
            "Example: 08:00 or 20:30\n\n"
            "Send /cancel to go back."
        )
        return WAITING_FOR_TIME

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    context.user_data['awaiting_time'] = False
    
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
    
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /hadith command"""
    await update.message.reply_text("⏳ Fetching hadith...")
    
    hadith = fetch_random_hadith()
    message = format_hadith_message(hadith)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Get Another Hadith", callback_data='get_hadith')],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def test_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test daily hadith immediately"""
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    jobs = context.job_queue.get_jobs_by_name(f"daily_hadith_{user_id}")
    
    if not jobs:
        await update.message.reply_text(
            "❌ Daily hadith is not enabled.\n\n"
            "Use /daily to set it up first."
        )
        return
    
    await update.message.reply_text("⏳ Sending test daily hadith...")
    
    hadith = fetch_random_hadith()
    message = format_hadith_message(hadith)
    message = "🧪 *Test Daily Hadith*\n\n" + message
    
    keyboard = [
        [InlineKeyboardButton("🔄 Get Another", callback_data='get_hadith')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='daily_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /daily command"""
    user_id = update.message.from_user.id
    jobs = context.job_queue.get_jobs_by_name(f"daily_hadith_{user_id}")
    is_enabled = len(jobs) > 0
    
    if is_enabled:
        message = (
            "⏰ *Daily Hadith Settings*\n\n"
            f"✅ Status: Enabled\n"
            f"🕐 Daily hadith is scheduled\n\n"
            "You will receive a hadith every day at your set time."
        )
    else:
        message = (
            "⏰ *Daily Hadith Settings*\n\n"
            "❌ Status: Disabled\n\n"
            "Enable daily hadiths to receive a hadith at the same time every day."
        )
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_daily_settings_keyboard(is_enabled)
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates"""
    logger.error(f"Exception while handling an update: {context.error}")

async def post_init(application: Application):
    """Restore scheduled jobs from database on bot startup"""
    logger.info("Restoring scheduled jobs from database...")
    
    users = get_all_daily_hadith_users()
    
    for user in users:
        user_id = user['user_id']
        chat_id = user['chat_id']
        time_obj = user['daily_hadith_time']
        timezone_str = user.get('timezone', 'Europe/Rome')
        
        if time_obj:
            try:
                if isinstance(time_obj, str):
                    hour, minute = map(int, time_obj.split(':'))
                elif hasattr(time_obj, 'hour') and hasattr(time_obj, 'minute'):

                    hour = time_obj.hour
                    minute = time_obj.minute
                else:
                    total_seconds = int(time_obj.total_seconds())
                    hour = total_seconds // 3600
                    minute = (total_seconds % 3600) // 60
                
                user_timezone = pytz.timezone(timezone_str)
                
                application.job_queue.run_daily(
                    send_daily_hadith,
                    time=time(hour=hour, minute=minute, tzinfo=user_timezone),
                    chat_id=chat_id,
                    name=f"daily_hadith_{user_id}",
                    user_id=user_id
                )
                
                logger.info(f"Restored daily hadith job for user {user_id} at {hour:02d}:{minute:02d} ({timezone_str})")
            except Exception as e:
                logger.error(f"Error restoring job for user {user_id}: {e}")
    
    logger.info(f"Restored {len(users)} scheduled jobs")

def main():
    """Start the bot"""
    init_database()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hadith", hadith_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("testdaily", test_daily_command))
    app.add_handler(CommandHandler("cancel", cancel))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_time_input
    ))
    
    app.add_error_handler(error_handler)
    
    logger.info("Bot is running... Press Ctrl+C to stop.")
    logger.info("Commands registered: /start, /hadith, /daily, /testdaily, /cancel")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()