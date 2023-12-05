from telegram import Update, BotCommand
from telegram.ext import Application

from bot import preferences, menu, system, fail2ban, docker, sendfiles
from bot.logger import logger


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("/menu", "Menu"),
        BotCommand("/start", "Start")
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.send_message(chat_id=preferences.owner_id, text="Bot started")


def main():
    logger.info("Starting")

    bot = (Application.builder()
           .token(preferences.bot_token)
           .post_init(post_init)
           .read_timeout(preferences.REPLY_TIMEOUT)
           .write_timeout(preferences.REPLY_TIMEOUT)
           .build())

    menu.init(bot)

    system.init(bot)
    fail2ban.init(bot)
    docker.init(bot)
    sendfiles.init(bot)

    bot.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
    logger.info("Bot stopped")
    