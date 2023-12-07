import ipaddress
import json
import socket
import struct
import subprocess
import time
from warnings import filterwarnings

import tailer
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove
from telegram.ext import Application, CallbackQueryHandler, ConversationHandler, CommandHandler, MessageHandler, \
    filters, ContextTypes
from telegram.warnings import PTBUserWarning

from bot import wrappers, mapping, utils
from bot.logger import logger

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

files = mapping.json_mapping['fail2ban_logs']

SELECT_JAIL, ENTER_IP = range(2)


def init(bot: Application):
    bot.add_handler(CallbackQueryHandler(_fail2ban_menu, pattern='^fail2ban$'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_unban_jail_menu, pattern='^fail2ban_unban$'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_unban_action, pattern='^fail2ban_unban_action_'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_unban_ip_menu, pattern='^fail2ban_unban_'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_logs_menu, pattern='^fail2ban_menu_logs_'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_logs_action, pattern='^fail2ban_logs_'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_start, pattern='^fail2ban_start$'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_stop, pattern='^fail2ban_stop$'))
    bot.add_handler(CallbackQueryHandler(_fail2ban_status, pattern='^fail2ban_status$'))

    slow_mode_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(_fail2ban_ban_menu, pattern='^fail2ban_ban$')],
        states={
            SELECT_JAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fail2ban_ban_ip_menu)],
            ENTER_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fail2ban_ban_action)],
        },
        fallbacks=[CommandHandler("cancel", utils.cancel_conv)],
    )
    bot.add_handler(slow_mode_handler)


############################# Menu #########################################


@wrappers.is_chat_allowed()
async def _fail2ban_menu(update, _):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _fail2ban_menu_message(),
        reply_markup=await _fail2ban_menu_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _fail2ban_ban_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(chat_id=query.message.chat_id, text=await _fail2ban_ban_jail_menu_message(),
                                   parse_mode=telegram.constants.ParseMode.HTML,
                                   reply_markup=await _fail2ban_ban_jail_menu_keyboard())
    return SELECT_JAIL


@wrappers.is_chat_allowed()
async def _fail2ban_ban_ip_menu(update: Update, context):
    context.user_data["jail"] = update.message.text

    reply_keyboard = [["/cancel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=True,
                                       input_field_placeholder="Enter IP:")

    await update.message.reply_text(text=await _fail2ban_ban_ip_menu_message(), reply_markup=reply_markup,
                                    parse_mode=telegram.constants.ParseMode.HTML)
    return ENTER_IP


@wrappers.is_chat_allowed()
async def _fail2ban_unban_jail_menu(update, _):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=await _fail2ban_unban_jail_menu_message(),
        reply_markup=await _fail2ban_unban_jail_menu_keyboard(),
        parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _fail2ban_unban_ip_menu(update, _):
    query = update.callback_query
    action = query.data
    await query.answer()
    await query.edit_message_text(
        text=await _fail2ban_unban_ip_menu_message(),
        reply_markup=await _fail2ban_unban_ip_menu_keyboard(action.split('_')[2], int(action.split('_')[3])),
        parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _fail2ban_logs_menu(update, _):
    query = update.callback_query
    data = query.data
    offset = int(data.split("fail2ban_menu_logs_", 1)[1])
    await query.answer()
    await query.edit_message_text(
        text=await _fail2ban_logs_menu_message(),
        reply_markup=await _fail2ban_logs_menu_keyboard(offset),
        parse_mode=telegram.constants.ParseMode.HTML)


############################# Messages #########################################


async def _fail2ban_menu_message():
    return '⛔️ <b>Fail2ban menu:</b>'


async def _fail2ban_unban_jail_menu_message():
    return '<b>Select jail:</b>'


async def _fail2ban_ban_jail_menu_message():
    return 'Select jail:'


async def _fail2ban_unban_ip_menu_message():
    return '<b>Select IP:</b>'


async def _fail2ban_ban_ip_menu_message():
    return 'Enter IP to ban:'


async def _fail2ban_logs_menu_message():
    return '<b>Select file:</b>'


############################ Keyboards #########################################


async def _fail2ban_menu_keyboard():
    keyboard = [[InlineKeyboardButton('▶️ Start', callback_data='fail2ban_start'),
                 InlineKeyboardButton('⏹ Stop', callback_data='fail2ban_stop')],
                [InlineKeyboardButton('⛔️ Ban IP', callback_data='fail2ban_ban'),
                 InlineKeyboardButton('🟢 Unban IP', callback_data='fail2ban_unban')],
                [InlineKeyboardButton('📄 Logs', callback_data='fail2ban_menu_logs_0'),
                 InlineKeyboardButton('📌 Status', callback_data='fail2ban_status')],
                [InlineKeyboardButton('↩️ Back to menu', callback_data='main_menu_back')]
                ]
    return InlineKeyboardMarkup(keyboard)


async def _fail2ban_ban_jail_menu_keyboard():
    reply_keyboard = []
    for jail in get_jails():
        reply_keyboard.append([f'{jail}'])
    reply_keyboard.append(["/cancel"])

    reply_markup = ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=True,
                                       input_field_placeholder="Select jail:")
    return reply_markup


async def _fail2ban_logs_menu_keyboard(offset: int):
    items_per_column = 10
    items_per_row = 2
    items_per_page = items_per_column * items_per_row
    keyboard = []

    bottom_menu = [InlineKeyboardButton('↩️ Back', callback_data='fail2ban')]

    keys = list(files.keys())
    for i in range(offset * items_per_page, min(len(keys), (offset + 1) * items_per_page), items_per_row):
        pair = [InlineKeyboardButton(keys[i], callback_data=f'fail2ban_logs_{keys[i]}'),
                InlineKeyboardButton(keys[i + 1], callback_data=f'fail2ban_logs_{keys[i + 1]}')] \
            if i + 1 < len(keys) else [InlineKeyboardButton(keys[i], callback_data=f'fail2ban_logs_{keys[i]}')]
        keyboard.append(pair)
    if offset > 0:
        bottom_menu.append(InlineKeyboardButton('◀️', callback_data=f'fail2ban_menu_logs_{offset - 1}'))
    if offset < int(len(keys) / items_per_page):
        bottom_menu.append(InlineKeyboardButton('▶️', callback_data=f'fail2ban_menu_logs_{offset + 1}'))
    keyboard.append(bottom_menu)
    return InlineKeyboardMarkup(keyboard)


async def _fail2ban_unban_jail_menu_keyboard():
    keyboard = []
    for jail in get_jails().split(' '):
        keyboard.append([InlineKeyboardButton(jail, callback_data=f'fail2ban_unban_{jail}_0')])
    keyboard.append([InlineKeyboardButton('↩️ Back', callback_data='fail2ban')])
    return InlineKeyboardMarkup(keyboard)


async def _fail2ban_unban_ip_menu_keyboard(jail: str, offset: int):
    items_per_column = 10
    items_per_row = 2
    items_per_page = items_per_column * items_per_row
    keyboard = []
    ips = sorted(get_banned_ips(jail), key=lambda ip: struct.unpack("!L", socket.inet_aton(ip))[0])
    bottom_menu = [InlineKeyboardButton('↩️ Back', callback_data='fail2ban')]

    for i in range(offset * items_per_page, min(len(ips), (offset + 1) * items_per_page), items_per_row):
        pair = [InlineKeyboardButton(ips[i], callback_data=f'fail2ban_unban_action_{jail}_{ips[i]}'),
                InlineKeyboardButton(ips[i + 1], callback_data=f'fail2ban_unban_action_{jail}_{ips[i + 1]}')] \
            if i + 1 < len(ips) else [
            InlineKeyboardButton(ips[i], callback_data=f'fail2ban_unban_action_{jail}_{ips[i]}')]
        keyboard.append(pair)
    if offset > 0:
        bottom_menu.append(InlineKeyboardButton('◀️', callback_data=f'fail2ban_unban_{jail}_{offset - 1}'))
    if offset < int(len(ips) / items_per_page):
        bottom_menu.append(InlineKeyboardButton('▶️', callback_data=f'fail2ban_unban_{jail}_{offset + 1}'))
    keyboard.append(bottom_menu)
    return InlineKeyboardMarkup(keyboard)


@wrappers.is_chat_allowed()
async def _fail2ban_start(update: Update, _) -> None:
    query = update.callback_query
    await query.answer()

    try:
        result = subprocess.run(["sudo", "service", "fail2ban", "start"], capture_output=True, text=True)
        if result.returncode == 0:
            msg_sent: Message = await query.edit_message_text(text="Successfully started fail2ban client.")
            time.sleep(3)
            await msg_sent.edit_text(text=await _fail2ban_menu_message(), reply_markup=await _fail2ban_menu_keyboard(),
                                     parse_mode=telegram.constants.ParseMode.HTML)
        else:
            logger.error(f"Failed to start fail2ban client: {result.returncode}")
            await query.edit_message_text(text=f"Failed to start fail2ban client: {result.returncode}")
    except Exception as e:
        logger.error(f"Failed to start fail2ban client: {e}")
        await query.edit_message_text(text=f"Failed to start fail2ban client: {e}")


@wrappers.is_chat_allowed()
async def _fail2ban_stop(update: Update, _) -> None:
    query = update.callback_query
    await query.answer()

    try:
        result = subprocess.run(["sudo", "service", "fail2ban", "stop"], capture_output=True, text=True)
        if result.returncode == 0:
            msg_sent: Message = await query.edit_message_text(text="Successfully stopped fail2ban client.")
            time.sleep(3)
            await msg_sent.edit_text(text=await _fail2ban_menu_message(), reply_markup=await _fail2ban_menu_keyboard(),
                                     parse_mode=telegram.constants.ParseMode.HTML)
        else:
            logger.error(f"Failed to stop fail2ban client: {result.returncode}")
            await query.edit_message_text(text=f"Failed to stop fail2ban client: {result.returncode}")
    except Exception as e:
        logger.error(f"Failed to stop fail2ban client: {e}")
        await query.edit_message_text(text=f"Failed to stop fail2ban client: {e}")


@wrappers.is_chat_allowed()
async def _fail2ban_status(update: Update, _) -> None:
    query = update.callback_query
    await query.answer()

    try:
        result = subprocess.run(["sudo", "service", "fail2ban", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            if query.message and query.message.text and query.message.text != result.stdout:
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('↩️ Back to menu', callback_data='fail2ban'),
                      InlineKeyboardButton("🔄 Refresh", callback_data='fail2ban_status')]])
                await query.edit_message_text(
                    text=f'```sudo service fail2ban status\n{result.stdout}```',
                    parse_mode=telegram.constants.ParseMode.MARKDOWN, reply_markup=keyboard)
        else:
            logger.error(f"Failed to get fail2ban client status: {result.returncode}")
            await query.edit_message_text(text=f"Failed to get fail2ban client status: {result.returncode}")
    except Exception as e:
        logger.error(f"Failed to get fail2ban client status: {e}")
        await query.edit_message_text(text=f"Failed to get fail2ban client status: {e}")


@wrappers.is_chat_allowed()
async def _fail2ban_unban_action(update: Update, _) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    jail = data.split('_')[3]
    ip_address = data.split('_')[4]

    try:
        result = subprocess.run(['fail2ban-client', 'set', jail, 'unbanip', ip_address], capture_output=True, text=True)
        if result.returncode == 0:
            msg_sent: Message = await query.edit_message_text(
                text=f"[{jail}] Successfully unbanned IP address: '{ip_address}'")
            time.sleep(3)
            await msg_sent.edit_text(text=await _fail2ban_menu_message(), reply_markup=await _fail2ban_menu_keyboard(),
                                     parse_mode=telegram.constants.ParseMode.HTML)
        else:
            logger.error(f"[{jail}] Failed to unban IP address '{ip_address}': {result.returncode}")
            await query.edit_message_text(
                text=f"[{jail}] Failed to unban IP address '{ip_address}': {result.returncode}")
    except Exception as e:
        logger.error(f"[{jail}] Failed to unban IP address '{ip_address}': {e}")
        await query.edit_message_text(text=f"[{jail}] Failed to unban IP address '{ip_address}': {e}")


@wrappers.is_chat_allowed()
async def _fail2ban_ban_action(update: Update, context):
    reply_markup = ReplyKeyboardRemove()
    try:
        ip_address = str(ipaddress.ip_address(update.message.text.strip()))
    except ValueError:
        logger.error(f"Invalid IP address '{update.message.text}', try again")
        await update.message.reply_text(text=f"Invalid IP address '{update.message.text}', try again",
                                        reply_markup=reply_markup)
        return ConversationHandler.END

    user_data = context.user_data
    if "jail" in user_data:
        jail = user_data["jail"]
        del user_data["jail"]

        try:
            result = subprocess.run(['fail2ban-client', 'set', jail, 'banip', ip_address], capture_output=True,
                                    text=True)
            if result.returncode == 0:
                await update.message.reply_text(text=f"[{jail}] Successfully banned IP address: '{ip_address}",
                                                reply_markup=reply_markup)
            else:
                logger.error(f"[{jail}] Failed to ban IP address '{ip_address}': {result.returncode}")
                await update.message.reply_text(
                    text=f"[{jail}] Failed to ban IP address '{ip_address}': {result.returncode}",
                    reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"[{jail}] Failed to ban IP address '{ip_address}': {e}")
            await update.message.reply_text(text=f"[{jail}] Failed to ban IP address '{ip_address}': {e}",
                                            reply_markup=reply_markup)
    return ConversationHandler.END


@wrappers.is_chat_allowed()
async def _fail2ban_logs_action(update: Update, _) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    file = data.split('_')[2]

    log = tailer.tail(open(files[file], encoding='utf-8'), 15)
    result = '\n'.join(map(str, log))
    if query.message and query.message.text and query.message.text != result:
        await query.edit_message_text(text=f'```{files[file]}\n{utils.get_last_n_characters(result, 4000)}```',
                                      parse_mode=telegram.constants.ParseMode.MARKDOWN,
                                      reply_markup=InlineKeyboardMarkup(
                                          [[InlineKeyboardButton('↩️ Back to logs',
                                                                 callback_data='fail2ban_menu_logs_0'),
                                            InlineKeyboardButton("🔄 Refresh", callback_data=data)]]))


def get_jails():
    result = subprocess.run(['fail2ban-client', 'banned'], capture_output=True, text=True)

    if result.returncode == 0:
        jail_list_line = [line for line in result.stdout.split('\n') if 'Jail list' in line][0]
        jail_list = subprocess.run(['sed', '-E', r's/^[^:]+:[ \t]+//', '-e', 's/,//g'], input=jail_list_line,
                                   capture_output=True, text=True)
        return jail_list.stdout.strip()
    else:
        logger.error(f"Command failed {result.stderr}")
        return None


def get_banned_ips(jail_name):
    result = subprocess.run(['fail2ban-client', 'banned', jail_name], capture_output=True, text=True)

    if result.returncode == 0:
        try:
            jail_info = json.loads(result.stdout)
            banned_ips = jail_info[jail_name]
            return banned_ips
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
    else:
        logger.error(f"Command failed {result.stderr}")
