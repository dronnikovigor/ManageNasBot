import telegram
import subprocess
import docker
import logging
import ipaddress
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler

# Replace 'YOUR_TELEGRAM_TOKEN' with your Telegram Bot API token
TELEGRAM_TOKEN = ''

# Replace 'YOUR_FAIL2BAN_JAIL' with the Fail2ban jail name (e.g., 'sshd', 'apache', etc.)
FAIL2BAN_JAIL = ['npm', 'nextcloud']

# Replace with the chat IDs of allowed users. Leave empty to disable user check
ALLOWED_USERS = []

# Replace path with your Nginx Proxy Manager log's path
NPM_LOGS = '/XXXXX/nginx-proxy-manager/data/logs'
FILES_TO_SEND = {
    "f2b log": "/var/log/fail2ban.log",
}

# States for the conversation handler
ENTER_IP, CONFIRM_RESTART_SYSTEM, CONFIRM_SHUTDOWN_SYSTEM, SELECT_CONTAINER, SELECT_JAIL, SELECT_FILE = range(6)

# Initialize Docker client
docker_client = docker.from_env()

# Init logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# Function to check if the user is allowed to use the bot
def is_allowed_user(update):
    if len(ALLOWED_USERS) > 0:
        user_id = update.effective_user.id
        logger.info(f'user id: {user_id}')
        return user_id in ALLOWED_USERS
    else:
        return True


##############################################################
###########              UNBAN                 ###############
##############################################################

def select_jail_to_unban(update, context):
    query = update.callback_query
    keyboard = [[InlineKeyboardButton(jail, callback_data=jail)] for jail in FAIL2BAN_JAIL]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text("Select jail to unban IP:", reply_markup=reply_markup)

    return SELECT_JAIL


def enter_ip_to_unban(update, context):
    query = update.callback_query
    context.user_data['jail_to_unban'] = query.data
    query.message.reply_text("Please enter the IP address you want to unban:")

    return ENTER_IP


# Function to unban the given IP address using fail2ban-client
def unban_ip(update, context):
    logger.info('unban ip')

    jail = context.user_data['jail_to_unban']
    if 'ip_to_unban' in context.user_data:
        logger.info('getting ip from memory')
        ip_address = context.user_data['ip_to_unban']
    else:
        logger.info('waiting for user ip')
        try:
            ip_address = str(ipaddress.ip_address(update.message.text.strip()))
        except ValueError:
            update.message.reply_text("Invalid IP address. Please enter a valid IP address.")
            return ENTER_IP

    if not is_valid_ip(ip_address):
        update.message.reply_text("Invalid IP. Please provide a valid IP address.")
        return ConversationHandler.END
    
    # Execute fail2ban-client command to unban the IP address
    try:
        result = subprocess.run(['fail2ban-client', 'set', jail, 'unbanip', ip_address], capture_output=True, text=True)
        if result.returncode == 0:
            context.user_data['ip_to_unban'] = ip_address
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Repeat", callback_data="unbanip_repeat")]])
            update.message.reply_text(f"[{jail}] Successfully unbanned IP address: {ip_address}", reply_markup=reply_markup)
        else:
            update.message.reply_text(f"Failed to unban IP address: {ip_address}")
    except Exception as e:
        update.message.reply_text(f"Error occurred: {e}")
        
    return ConversationHandler.END


# Helper function to check if the provided string is a valid IP address
def is_valid_ip(ip_address):
    # You can implement a custom IP address validation logic here
    return True

    
##############################################################
###########              RESTART               ###############
##############################################################

def restart_system(update, context):
    logger.info("restart_system")
    query = update.callback_query

    if query.data == 'restart:yes':
        try:
            # Execute the system reboot command using subprocess
            subprocess.run(['reboot'])
            query.message.reply_text("System is restarting. The bot will be back online shortly.")
        except Exception as e:
            query.message.reply_text(f"Failed to restart the system: {e}")
    else:
        query.message.reply_text("Restart has been canceled.")

    return ConversationHandler.END


def shutdown_system(update, context):
    logger.info("shutdown_system")
    query = update.callback_query

    if query.data == 'shutdown:yes':
        try:
            # Execute the system shutdown command using subprocess
            subprocess.run(['shutdown', '-h', 'now'])
            query.message.reply_text("System is shutting down. The bot will be offline now.")
        except Exception as e:
            query.message.reply_text(f"Failed to shut down the system: {e}")
    else:
        query.message.reply_text("Shutdown has been canceled.")

    return ConversationHandler.END


##############################################################
###########              DOCKER                ###############
##############################################################

def restart_docker_container(update, context):
    logger.info("restart_docker_container")
    query = update.callback_query
    docker_client = docker.from_env()
    containers = docker_client.containers.list()

    if not containers:
        query.message.reply_text("No running Docker containers found.")
        return

    keyboard = [[InlineKeyboardButton(container.name, callback_data=container.name)] for container in containers]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text("Select a Docker container to restart:", reply_markup=reply_markup)

    return SELECT_CONTAINER


def handle_container_selection(update, context):
    logger.info("handle_container_selection")
    query = update.callback_query

    docker_client = docker.from_env()
    container_name = query.data

    try:
        container = docker_client.containers.get(container_name)
        container.restart()
        query.message.reply_text(f"Container '{container_name}' has been restarted.")
    except docker.errors.NotFound:
        query.message.reply_text(f"Container '{container_name}' not found.")
    except docker.errors.APIError:
        query.message.reply_text(f"Error restarting container '{container_name}'. Please try again later.")

    return ConversationHandler.END


##############################################################
###########               SENDFILE             ###############
##############################################################

def select_file_to_send(update, context):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton(f"{file}", callback_data=file)] for file in FILES_TO_SEND]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text("Select file to send:", reply_markup=reply_markup)

    return SELECT_FILE


def send_file(update, context):
    query = update.callback_query

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_document(chat_id=query.message.chat_id, document=open(FILES_TO_SEND[query.data], 'rb'))

    return ConversationHandler.END


##############################################################
###########              MENU                  ###############
##############################################################
        
def show_menu(update, context):
    if not is_allowed_user(update):
        update.message.reply_text("You are not allowed to use this bot.")
        return

    logger.info('/start')
    # Create the main menu with available options
    update.message.reply_text("#menu\nSelect action:", reply_markup=get_menu_keyboard())


def get_menu_keyboard():
    menu_options = [
        [InlineKeyboardButton("🔄 Restart System", callback_data="restart")],
        [InlineKeyboardButton("⏹ Shutdown System", callback_data="shutdown")],
        [InlineKeyboardButton("📋 Unban IP", callback_data="unbanip")],
        [InlineKeyboardButton("🔄 Restart Docker Container", callback_data="restartdocker")],
        [InlineKeyboardButton("🔄 Start fail2ban", callback_data='startfail2ban')],
        [InlineKeyboardButton("⏹ Stop fail2ban", callback_data='stopfail2ban')],
        [InlineKeyboardButton("📋 Send files", callback_data='sendfiles')],
    ]
    return InlineKeyboardMarkup(menu_options, resize_keyboard=True, one_time_keyboard=True)


def menu_click(update, context):
    logger.info('button click')
    query = update.callback_query
    action = query.data

    if action == 'restart':
        query.message.reply_text("Are you sure you want to restart the system?",
                                 reply_markup=get_confirmation_keyboard('restart'))
        return CONFIRM_RESTART_SYSTEM
    elif action == 'shutdown':
        query.message.reply_text("Are you sure you want to shut down the system?",
                                 reply_markup=get_confirmation_keyboard('shutdown'))
        return CONFIRM_SHUTDOWN_SYSTEM
    elif action == 'unbanip':
        if 'ip_to_unban' in context.user_data:
            context.user_data.pop('ip_to_unban')
            context.user_data.pop('jail_to_unban')
        return select_jail_to_unban(update, context)
    elif action == 'unbanip_repeat':
        query.message.reply_text("Repeating Unban IP...")
        return unban_ip(query, context)
    elif action == 'restartdocker':
        return restart_docker_container(update, context)
    elif action == 'startfail2ban':
        # Start fail2ban logic
        subprocess.run(["sudo", "service", "fail2ban", "start"])
        query.message.reply_text("fail2ban service started.")
    elif action == 'stopfail2ban':
        # Stop fail2ban logic
        subprocess.run(["sudo", "service", "fail2ban", "stop"])
        query.message.reply_text("fail2ban service stopped.")
    elif query.data == 'sendfiles':
        return select_file_to_send(update, context)
    else:
        query.message.reply_text("Incorrect action")


def get_confirmation_keyboard(action_type):
    yes_button = InlineKeyboardButton("Yes", callback_data=f"{action_type}:yes")
    no_button = InlineKeyboardButton("No", callback_data=f"{action_type}:no")
    keyboard = [[yes_button, no_button]]
    return InlineKeyboardMarkup(keyboard)


##############################################################
###########               MAIN                 ###############
##############################################################

def main():
    # Create the Telegram bot and updater
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Register the /start command handler to show the main menu
    dp.add_handler(CommandHandler("start", show_menu))

    # Register the conversation handler for system restart and shutdown confirmation
    dp.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_click)],
        states={
            CONFIRM_RESTART_SYSTEM: [CallbackQueryHandler(restart_system)],
            CONFIRM_SHUTDOWN_SYSTEM: [CallbackQueryHandler(shutdown_system)],
            SELECT_CONTAINER: [CallbackQueryHandler(handle_container_selection)],
            ENTER_IP: [MessageHandler(Filters.text & ~Filters.command, unban_ip)],
            SELECT_JAIL: [CallbackQueryHandler(enter_ip_to_unban)],
            SELECT_FILE: [CallbackQueryHandler(send_file)]
        },
        fallbacks=[]
    ))

    # Start the Bot
    updater.start_polling()
    updater.idle()

    logger.info('started')

if __name__ == '__main__':
    main()
    