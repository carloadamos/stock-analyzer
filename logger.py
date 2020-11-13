import logging

# Logger
logging.basicConfig(filename='executions.log', level=logging.DEBUG,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def error_logger(message):
    logging.error(message)


def info_logger(message):
    logging.info(message)


def warning_logger(message):
    logging.warning(message)
