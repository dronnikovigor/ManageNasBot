import time

import docker
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler

from bot import wrappers, utils
from bot.logger import logger


def init(bot: Application):
    bot.add_handler(CallbackQueryHandler(_docker_menu, pattern='^docker_main_menu_'))
    bot.add_handler(CallbackQueryHandler(_docker_action_menu, pattern='^docker_container_'))
    bot.add_handler(CallbackQueryHandler(_docker_restart, pattern='^docker_restart_'))
    bot.add_handler(CallbackQueryHandler(_docker_stop, pattern='^docker_stop_'))
    bot.add_handler(CallbackQueryHandler(_docker_logs, pattern='^docker_logs_'))


############################# Menu #########################################


@wrappers.is_chat_allowed()
async def _docker_menu(update, _):
    query = update.callback_query
    action = query.data
    await query.answer()
    await query.edit_message_text(
        text=await _docker_menu_message(),
        reply_markup=await _docker_menu_keyboard(int(action.split('_')[3])),
        parse_mode=telegram.constants.ParseMode.HTML)


@wrappers.is_chat_allowed()
async def _docker_action_menu(update, _):
    query = update.callback_query
    data = query.data
    container_name = data.split("docker_container_", 1)[1]
    await query.answer()
    await query.edit_message_text(
        text=await _docker_action_menu_message(container_name),
        reply_markup=await _docker_action_menu_keyboard(container_name),
        parse_mode=telegram.constants.ParseMode.HTML)


############################# Messages #########################################


async def _docker_menu_message():
    return '🗳 <b>Select container:</b>'


async def _docker_action_menu_message(container_name: str):
    return f'<b>Select action for container "{container_name}":</b>'


############################ Keyboards #########################################


async def _docker_menu_keyboard(offset: int):
    docker_client = docker.from_env()
    containers = docker_client.containers.list()

    items_per_column = 10
    items_per_row = 2
    items_per_page = items_per_column * items_per_row
    keyboard = []

    containers_sorted = sorted(containers, key=lambda x: x.name)
    bottom_menu = [InlineKeyboardButton('↩️ Back to menu', callback_data='main_menu_back')]

    for i in range(offset * items_per_page, min(len(containers_sorted), (offset + 1) * items_per_page), items_per_row):
        pair = [InlineKeyboardButton(containers_sorted[i].name,
                                     callback_data=f'docker_container_{containers_sorted[i].name}'),
                InlineKeyboardButton(containers_sorted[i + 1].name,
                                     callback_data=f'docker_container_{containers_sorted[i + 1].name}')] \
            if i + 1 < len(containers_sorted) else [
            InlineKeyboardButton(containers_sorted[i].name,
                                 callback_data=f'docker_container_{containers_sorted[i].name}')]
        keyboard.append(pair)
    if offset > 0:
        bottom_menu.append(InlineKeyboardButton('◀️', callback_data=f'docker_main_menu_{offset - 1}'))
    if offset < int(len(containers_sorted) / items_per_page):
        bottom_menu.append(InlineKeyboardButton('▶️', callback_data=f'docker_main_menu_{offset + 1}'))
    keyboard.append(bottom_menu)
    return InlineKeyboardMarkup(keyboard)


async def _docker_action_menu_keyboard(container_name: str):
    keyboard = [
        [InlineKeyboardButton('Restart', callback_data=f'docker_restart_{container_name}')],
        [InlineKeyboardButton('Stop', callback_data=f'docker_stop_{container_name}')],
        [InlineKeyboardButton('Logs', callback_data=f'docker_logs_{container_name}')],
        [InlineKeyboardButton('↩️ Back to menu', callback_data='docker_main_menu_0')],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _docker_restart(update, _):
    query = update.callback_query
    data: str = query.data
    container_name = data.split("docker_restart_", 1)[1]
    await query.answer()
    docker_client = docker.from_env()

    try:
        logger.debug(f"Restarting container '{container_name}'")
        container = docker_client.containers.get(container_name)
        container.restart()
        msg_sent = await query.edit_message_text(f"Container '{container_name}' has been restarted.")
        time.sleep(3)
        await msg_sent.edit_text(text=await _docker_action_menu_message(container_name),
                                 reply_markup=await _docker_action_menu_keyboard(container_name),
                                 parse_mode=telegram.constants.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Exception during restarting container '{container_name}': {e}")
        await query.edit_message_text(f"Exception during restarting container '{container_name}': {e}")


async def _docker_stop(update, _):
    query = update.callback_query
    data = query.data
    container_name = data.split("docker_stop_", 1)[1]
    await query.answer()

    try:
        logger.debug(f"Stopping container '{container_name}'")
        docker_client = docker.from_env()
        docker_client.containers.get(container_name).stop()
        msg_sent = await query.edit_message_text(f"Container '{container_name}' has been stopped.")
        time.sleep(3)
        await msg_sent.edit_text(text=await _docker_menu_message(),
                                 reply_markup=await _docker_menu_keyboard(0),
                                 parse_mode=telegram.constants.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Exception during stopping container '{container_name}': {e}")
        await query.edit_message_text(f"Exception during stopping container '{container_name}': {e}")


async def _docker_logs(update, _):
    tail = 10
    query = update.callback_query
    data = query.data
    container_name = data.split("docker_logs_", 1)[1]
    await query.answer()

    try:
        logger.debug(f"Getting logs for container '{container_name}'")
        docker_client = docker.from_env()
        logs = docker_client.containers.get(container_name).logs(stream=True, follow=False, tail=tail, timestamps=True)
        result_logs = ''
        for i in range(tail):
            result_logs += next(logs).decode("utf-8")
        if query.message and query.message.text and query.message.text != result_logs.strip():
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton('↩️ Back to menu', callback_data=f'docker_container_{container_name}'),
                  InlineKeyboardButton("🔄 Refresh", callback_data=f'docker_logs_{container_name}')]])
            await query.edit_message_text(text=f'```{container_name}\n{utils.get_last_n_characters(result_logs.strip(), 4000)}```',
                                          parse_mode=telegram.constants.ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Exception during getting logs of container '{container_name}': {e}")
        await query.edit_message_text(f"Exception during getting logs of container '{container_name}': {e}")
