# Standard library
import logging
import logging.handlers
from os import path
from sys import stdout
# Third party library
# Local library
from warehouse.server import config


def initialize_logs():
    log = logging.getLogger()
    # Must set "base" level logging. If base is not set, defaults to WARNING, which won't read anything less
    # than WARNING in subsequent loggers
    log.setLevel(logging.DEBUG)
    # Set up global format
    log_format = logging.Formatter("{asctime}.{msecs:03.0f}:{levelname:<8} - {message} - {module}.{funcName}({lineno})",
                                   datefmt="%H:%M:%S", style="{")

    config_file_log(log, log_format)
    config_normal_operation_log(log, log_format)
    config_log_with_ip_addresses(log_format)
    reconfig_tornado_log()


def config_file_log(logger, formatter):
    # Set up a rotating log at BASE_DIR/../warehouse.log
    # Time rotated log, responsible for WARNINGs and higher
    # Rotated every day at midnight
    rotating_handler = logging.handlers.TimedRotatingFileHandler(path.abspath(path.join(config.BASE_DIR, "..", "warehouse.log")),
                                                                 when="midnight", backupCount=3)
    rotating_handler.setLevel(logging.WARNING)
    rotating_handler.setFormatter(formatter)
    logger.addHandler(rotating_handler)


def config_normal_operation_log(logger, formatter):
    # Use a mail handler for critical errors when not in DEBUG
    # Emails to wgordon@masline.com from warehouse_app@masline.com
    # Only responsible for CRITICAL errors
    if not config.DEBUG:
        mail_handler = logging.handlers.SMTPHandler(mailhost="mail.masline.com",
                                                    fromaddr="warehouse_app@masline.com",
                                                    toaddrs=["wgordon@masline.com"],
                                                    subject="CRITICAL error on warehouse")
        mail_handler.setLevel(logging.CRITICAL)
        mail_handler.setFormatter(formatter)
        logger.addHandler(mail_handler)
    # Report ALL logs to stdout/stderr when in DEBUG
    else:
        # Stdout handles all logs in DEBUG mode. Colored output in PyCharm, thanks to Grep Console, differentiates output
        stdout_handler = logging.StreamHandler(stream=stdout)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)


def config_log_with_ip_addresses(log_format):
    logger = logging.getLogger("warehouse.server.handlers")
    # noinspection PyProtectedMember
    extra_format = logging.Formatter(log_format._fmt + " - {ip}({user})", datefmt=log_format.datefmt, style="{")
    if not config.DEBUG:
        ip_handler = logging.handlers.TimedRotatingFileHandler(path.abspath(path.join(config.BASE_DIR, "..", "warehouse.log")),
                                                                 when="midnight", backupCount=3)
        ip_handler.setLevel(logging.WARNING)
    else:
        ip_handler = logging.StreamHandler(stream=stdout)
        ip_handler.setLevel(logging.DEBUG)
    ip_handler.setFormatter(extra_format)
    logger.addHandler(ip_handler)
    # Prevents these logs from duplicated by parent loggers
    logger.propagate = False


def reconfig_tornado_log():
    logger = logging.getLogger("tornado.access")
    logger.setLevel(logging.WARNING)
