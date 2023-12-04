import time

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes, Application, CallbackQueryHandler

from bot import wrappers
from bot.logger import logger

APPROVE_REBOOT, APPROVE_SHUTDOWN = range(2)


def init(bot: Application):
    bot.add_handler(CallbackQueryHandler(_system_menu, pattern='^system$'))
    bot.add_handler(CallbackQueryHandler(_system_reboot_menu, pattern='^system_reboot$'))
    bot.add_handler(CallbackQueryHandler(_system_shutdown_menu, pattern='^system_shutdown$'))
    bot.add_handler(CallbackQueryHandler(_system_reboot_action, pattern='^system_reboot_'))
    bot.add_handler(CallbackQueryHandler(_system_shutdown_action, pattern='^system_shutdown_'))


############################# Menu #########################################


@wrappers.is_chat_allowed()
async def _system_menu(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _system_menu_message(),
        reply_markup=await _system_menu_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _system_reboot_menu(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _system_reboot_message(),
        reply_markup=await _system_reboot_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _system_shutdown_menu(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _system_shutdown_message(),
        reply_markup=await _system_shutdown_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


############################# Messages #########################################


async def _system_menu_message():
    return '🔄 <b>System menu:</b>'


async def _system_reboot_message():
    return '<b>Are you sure you want to reboot system?</b>'


async def _system_shutdown_message():
    return '<b>Are you sure you want to shutdown system?</b>'


############################ Keyboards #########################################


async def _system_menu_keyboard():
    keyboard = [[InlineKeyboardButton('🔄 Reboot', callback_data='system_reboot'),
                 InlineKeyboardButton('⏹ Shutdown', callback_data='system_shutdown')],
                [InlineKeyboardButton('↩️ Back to menu', callback_data='main_menu_back')]
                ]
    return InlineKeyboardMarkup(keyboard)


async def _system_reboot_keyboard():
    keyboard = [[InlineKeyboardButton('YES', callback_data='system_reboot_yes'),
                 InlineKeyboardButton('NO', callback_data='system_reboot_no')]
                ]
    return InlineKeyboardMarkup(keyboard)


async def _system_shutdown_keyboard():
    keyboard = [[InlineKeyboardButton('YES', callback_data='system_shutdown_yes'),
                 InlineKeyboardButton('NO', callback_data='system_shutdown_no')]
                ]
    return InlineKeyboardMarkup(keyboard)


@wrappers.is_chat_allowed()
async def _system_reboot_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    action = query.data
    if action.endswith('yes'):
        try:
            logger.info('Restarting system')
            # todo uncomment
            # subprocess.run(['reboot'])
            await query.edit_message_text(text="System is restarting. The bot will be back online shortly.")
        except Exception as e:
            logger.error(f"Failed to restart the system: {e}")
            await query.edit_message_text(text=f"Failed to restart the system: {e}")
    else:
        msg_sent: Message = await query.edit_message_text(text="Restart has been canceled.")
        time.sleep(3)
        await msg_sent.edit_text(text=await _system_menu_message(), reply_markup=await _system_menu_keyboard(),
                                 parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _system_shutdown_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    action = query.data
    if action.endswith('yes'):
        try:
            logger.info('Shutting down system')
            # todo uncomment
            # subprocess.run(['shutdown', '-h', 'now'])
            await query.edit_message_text(text="System is shutting down. The bot will be offline now.")
        except Exception as e:
            logger.error(f"Failed to shut down the system: {e}")
            await query.edit_message_text(text=f"Failed to shut down the system: {e}")
    else:
        msg_sent = await query.edit_message_text(text="Shutdown has been canceled.")
        time.sleep(3)
        await msg_sent.edit_text(text=await _system_menu_message(), reply_markup=await _system_menu_keyboard(),
                                 parse_mode=telegram.constants.ParseMode.HTML)
