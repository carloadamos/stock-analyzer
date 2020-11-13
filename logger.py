import logging
import os

os.remove('logs/executions.log')

# Logger
logging.basicConfig(filename='logs/executions.log', level=logging.DEBUG,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def error_logger(message):
    logging.error(message)
    print(message)


def info_logger(message):
    logging.info(message)
    print(message)


def warning_logger(message):
    logging.warning(message)
    print(message)
