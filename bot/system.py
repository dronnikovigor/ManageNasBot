import telegram
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, Application, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters

from bot import wrappers
from bot.logger import logger

APPROVE_REBOOT, APPROVE_SHUTDOWN = range(2)


def init(bot: Application):
    bot.add_handler(CallbackQueryHandler(_system_menu, pattern='^system$'))

    system_reboot_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(_system_reboot, pattern='system_reboot')],
        states={
            APPROVE_REBOOT: [MessageHandler(filters.Regex("^(YES|NO)$"), _system_reboot_end)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )
    bot.add_handler(system_reboot_handler)

    system_shutdown_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(_system_shutdown, pattern='system_shutdown')],
        states={
            APPROVE_SHUTDOWN: [MessageHandler(filters.Regex("^(YES|NO)$"), _system_shutdown_end)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )
    bot.add_handler(system_shutdown_handler)


@wrappers.is_chat_allowed()
async def _system_menu(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _system_menu_message(),
        reply_markup=await _system_menu_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


############################# Messages #########################################


async def _system_menu_message():
    return '🔄 <b>System menu:</b>'


############################ Keyboards #########################################


async def _system_menu_keyboard():
    keyboard = [[InlineKeyboardButton('🔄 Reboot', callback_data='system_reboot')],
                [InlineKeyboardButton('⏹ Shutdown', callback_data='system_shutdown')],
                [InlineKeyboardButton('↩️ Back to menu', callback_data='main_menu_back')]
                ]
    return InlineKeyboardMarkup(keyboard)


@wrappers.is_chat_allowed()
async def _system_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    reply_keyboard = [['YES', 'NO'], ["/cancel"]]

    reply_markup = ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=True,
                                       input_field_placeholder="Select option:")
    await context.bot.send_message(text="Are you sure you want to reboot system?",
                                   chat_id=update.effective_chat.id, reply_to_message_id=update.effective_message.id,
                                   reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.HTML)
    return APPROVE_REBOOT


# Function to manage system
@wrappers.is_chat_allowed()
async def _system_reboot_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("restart_system")

    if update.message.text == "YES":
        try:
            # subprocess.run(['reboot'])
            await update.message.reply_text("System is restarting. The bot will be back online shortly.",
                                            reply_to_message_id=update.effective_message.id)
        except Exception as e:
            await update.message.reply_text(f"Failed to restart the system: {e}",
                                            reply_to_message_id=update.effective_message.id)
    else:
        await update.message.reply_text("Restart has been canceled.",
                                        reply_to_message_id=update.effective_message.id)

    return ConversationHandler.END


# Stop conversation
async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Canceled", reply_markup=ReplyKeyboardRemove(),
        reply_to_message_id=update.effective_message.id
    )

    return ConversationHandler.END


@wrappers.is_chat_allowed()
async def _system_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    reply_keyboard = [['YES', 'NO'], ["/cancel"]]

    reply_markup = ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=True,
                                       input_field_placeholder="Select option:")
    await context.bot.send_message(text="Are you sure you want to shutdown system?",
                                   chat_id=update.effective_chat.id, reply_to_message_id=update.effective_message.id,
                                   reply_markup=reply_markup, parse_mode=telegram.constants.ParseMode.HTML)
    return APPROVE_SHUTDOWN


# Function to manage system
@wrappers.is_chat_allowed()
async def _system_shutdown_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("system_shutdown")

    if update.message.text == "YES":
        try:
            # subprocess.run(['shutdown', '-h', 'now'])
            await update.message.reply_text("System is shutting down. The bot will be offline now.",
                                            reply_to_message_id=update.effective_message.id)
        except Exception as e:
            await update.message.reply_text(f"Failed to shut down the system: {e}",
                                            reply_to_message_id=update.effective_message.id)
    else:
        await update.message.reply_text("Shutdown has been canceled.",
                                        reply_to_message_id=update.effective_message.id)

    return ConversationHandler.END
