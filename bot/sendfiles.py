import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CallbackQueryHandler

from bot import mapping
from bot import wrappers
from bot.logger import logger

files = mapping.json_mapping['files_to_download']


def init(bot: Application):
    bot.add_handler(CallbackQueryHandler(_sendfiles_menu, pattern='^sendfiles_menu_'))
    bot.add_handler(CallbackQueryHandler(_sendfile, pattern='^sendfile_'))


############################# Menu #########################################


@wrappers.is_chat_allowed()
async def _sendfiles_menu(update, _):
    query = update.callback_query
    data = query.data
    offset = int(data.split("sendfiles_menu_", 1)[1])
    await query.answer()
    await query.edit_message_text(
        text=await _sendfiles_menu_message(),
        reply_markup=await _sendfiles_menu_keyboard(offset),
        parse_mode=telegram.constants.ParseMode.HTML)


############################# Messages #########################################


async def _sendfiles_menu_message():
    return '📁 <b>Select file to download:</b>'


############################ Keyboards #########################################


async def _sendfiles_menu_keyboard(offset: int):
    items_per_column = 10
    items_per_row = 2
    items_per_page = items_per_column * items_per_row
    keyboard = []

    bottom_menu = [InlineKeyboardButton('↩️ Back to menu', callback_data='main_menu_back')]

    keys = list(files.keys())
    for i in range(offset * items_per_page, min(len(keys), (offset + 1) * items_per_page), items_per_row):
        pair = [InlineKeyboardButton(keys[i], callback_data=f'sendfile_{keys[i]}'),
                InlineKeyboardButton(keys[i+1], callback_data=f'sendfile_{keys[i+1]}')] \
            if i + 1 < len(keys) else [InlineKeyboardButton(keys[i], callback_data=f'sendfile_{keys[i]}')]
        keyboard.append(pair)
    if offset > 0:
        bottom_menu.append(InlineKeyboardButton('◀️', callback_data=f'sendfiles_menu_{offset - 1}'))
    if offset < int(len(keys) / items_per_page):
        bottom_menu.append(InlineKeyboardButton('▶️', callback_data=f'sendfiles_menu_{offset + 1}'))
    keyboard.append(bottom_menu)
    return InlineKeyboardMarkup(keyboard)


async def _sendfile(update, context):
    query: CallbackQuery = update.callback_query
    data = query.data
    file = data.split("sendfile_", 1)[1]
    await query.answer()
    logger.debug(f"Sending file '{files[file]}'")
    await context.bot.send_document(chat_id=query.message.chat_id, document=open(files[file], 'rb'))
