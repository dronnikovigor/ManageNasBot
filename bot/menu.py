import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from bot import wrappers


def init(bot: Application):
    bot.add_handler(CommandHandler("menu", callback=_main_menu))
    bot.add_handler(CallbackQueryHandler(_main_menu_back, pattern='main_menu_back'))


@wrappers.is_message_from_bot_owner()
async def _main_menu(update, context):
    await update.message.reply_text(await _main_menu_message(),
                                    reply_markup=await _main_menu_keyboard(),
                                    parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _main_menu_back(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _main_menu_message(),
        reply_markup=await _main_menu_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


############################# Messages #########################################


async def _main_menu_message():
    return '📍<b>Menu:</b>'


############################ Keyboards #########################################


async def _main_menu_keyboard():
    keyboard = [[InlineKeyboardButton('🔄 System', callback_data='system')],
                [InlineKeyboardButton('🗳 Docker', callback_data='docker')],
                [InlineKeyboardButton('⛔️ fail2ban', callback_data='fail2ban')],
                [InlineKeyboardButton('📁 Files', callback_data='files')]
                ]
    return InlineKeyboardMarkup(keyboard)
