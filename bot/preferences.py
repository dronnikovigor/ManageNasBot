import configparser


config = configparser.ConfigParser()
config.read('config.ini')

bot_token = config.get('Telegram', 'bot_token')
owner_id = int(config.get('Telegram', 'owner_id'))

REPLY_TIMEOUT = 90