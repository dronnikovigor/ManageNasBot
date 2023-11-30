import logging
from logging.handlers import TimedRotatingFileHandler

log_formatter = logging.Formatter("[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")

log_file_name = './logs/log.log'
handler_log_level = logging.DEBUG
logger_log_level = logging.DEBUG

handler = TimedRotatingFileHandler(log_file_name, when="midnight", backupCount=30, encoding='utf-8')
handler.suffix = "%Y%m%d"
handler.setLevel(handler_log_level)
handler.setFormatter(log_formatter)

logger = logging.getLogger('logs')
logger.addHandler(handler)
logger.setLevel(logger_log_level)
