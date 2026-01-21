import logging
import asyncio
import re
from datetime import timedelta, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler,
    CommandHandler
)
from config import BOT_TOKEN, CHANNEL_ID, OWNER_ID

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States for ConversationHandler
CHOOSING_ACTION = 0
TYPING_TIME = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    user_id = str(update.effective_user.id)
    if user_id != str(OWNER_ID):
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 **Hello Owner!**\n\n"
            "Send me any post (text, media, etc.).\n"
            "I will ask if you want to **Post Now** or **Schedule** it."
        ),
        parse_mode="Markdown"
    )

async def ask_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when user sends a message/media.
    Saves the message ID and asks "Post Now or Schedule?".
    """
    user_id = str(update.effective_user.id)
    if user_id != str(OWNER_ID):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Access Denied.")
        return ConversationHandler.END

    # Save the message object to context.user_data to use later
    # We copy the message ID and chat ID to reference it
    context.user_data['message_to_post_id'] = update.effective_message.message_id
    context.user_data['from_chat_id'] = update.effective_chat.id

    # Create Buttons
    keyboard = [
        [
            InlineKeyboardButton("🚀 Post Now", callback_data='post_now'),
            InlineKeyboardButton("📅 Schedule", callback_data='schedule'),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Reply to the message with options
    await update.message.reply_text(
        "What do you want to do with this post?",
        reply_markup=reply_markup,
        reply_to_message_id=update.message.message_id
    )

    return CHOOSING_ACTION

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the button clicks: Post Now, Schedule, or Cancel."""
    query = update.callback_query
    await query.answer() # Acknowledge the click
    
    choice = query.data

    if choice == 'cancel':
        await query.edit_message_text("❌ Action cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    elif choice == 'post_now':
        # Execute post immediately
        await perform_post_now(context, query)
        return ConversationHandler.END

    elif choice == 'schedule':
        await query.edit_message_text(
            "⏳ **Schedule Post**\n\n"
            "Enter the time delay from now.\n"
            "Examples:\n"
            "• `10s` (10 seconds)\n"
            "• `5m` (5 minutes)\n"
            "• `1h` (1 hour)\n\n"
            "Reply with the time:",
            parse_mode="Markdown"
        )
        return TYPING_TIME

async def perform_post_now(context, query):
    """Helper to post immediately."""
    try:
        msg_id = context.user_data.get('message_to_post_id')
        from_chat = context.user_data.get('from_chat_id')
        
        if not msg_id or not from_chat:
            await query.edit_message_text("❌ Error: Message data lost.")
            return

        await context.bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=from_chat,
            message_id=msg_id
        )
        await query.edit_message_text("✅ **Posted Successfully!**", parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Post Now Error: {e}")
        await query.edit_message_text(f"❌ Failed: {e}")

async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses time input (relative or absolute) and schedules the job."""
    time_str = update.message.text.strip().lower()
    now = datetime.now()
    delay_seconds = 0
    readable_time = ""

    # 1. Try Relative Time (e.g., 10m, 1h)
    relative_match = re.match(r'^(\d+)([smh])$', time_str)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        delta = timedelta()
        if unit == 's': delta = timedelta(seconds=amount)
        elif unit == 'm': delta = timedelta(minutes=amount)
        elif unit == 'h': delta = timedelta(hours=amount)
        
        delay_seconds = delta.total_seconds()
        readable_time = (now + delta).strftime("%Y-%m-%d %H:%M:%S")

    # 2. Try Absolute Time (e.g., 4:00 pm, 16:00)
    else:
        try:
            # Try parsing various formats
            target_time = None
            for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
                try:
                    # Parse time only
                    dt_time = datetime.strptime(time_str, fmt).time()
                    # Combine with today's date
                    target_time = datetime.combine(now.date(), dt_time)
                    break
                except ValueError:
                    continue
            
            if target_time:
                # If time has passed today, move to tomorrow
                if target_time <= now:
                    target_time += timedelta(days=1)
                
                delay_seconds = (target_time - now).total_seconds()
                readable_time = target_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                raise ValueError("No valid format found")

        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format.\n"
                "Try relative: `10m`, `1h`\n"
                "Or specific time: `4:00 pm`, `16:30`"
            )
            return TYPING_TIME

    # Schedule the job
    job_data = {
        'message_id': context.user_data.get('message_to_post_id'),
        'from_chat_id': context.user_data.get('from_chat_id'),
        'user_chat_id': update.effective_chat.id
    }

    context.job_queue.run_once(execute_scheduled_post, delay_seconds, data=job_data)

    await update.message.reply_text(
        f"✅ Post scheduled!\n"
        f"It will be posted at: **{readable_time}** (Server Time)",
        parse_mode="Markdown"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def execute_scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    """The job function that runs after the delay."""
    job = context.job
    data = job.data
    
    try:
        await context.bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=data['from_chat_id'],
            message_id=data['message_id']
        )
        # Notify user (optional, can check if blocking)
        await context.bot.send_message(chat_id=data['user_chat_id'], text="🔔 Your scheduled post has been sent!")
        
    except Exception as e:
        logging.error(f"Scheduled Post Error: {e}")
        await context.bot.send_message(chat_id=data['user_chat_id'], text=f"❌ Scheduled post failed: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the conversation."""
    await update.message.reply_text("❌ Cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation Handler manages the flow
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.ALL & (~filters.COMMAND), ask_action)],
        states={
            CHOOSING_ACTION: [CallbackQueryHandler(button_handler)],
            TYPING_TIME: [MessageHandler(filters.TEXT & (~filters.COMMAND), receive_time)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(button_handler) # To handle 'cancel' button in CHOOSING state
        ]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    print("Bot is running with Scheduling...")
    application.run_polling()
