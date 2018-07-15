import logging
import colorlog
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s'))
logger.addHandler(handler)

def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    logger.error('error')
    logger.debug('debug')
    pass


def colorlog_sandbox():

    logger.error('エラー')
    logger.debug('でばっぐ')
    logger.info('いんふぉ')
    logger.warning('わーにんぐ')
    logger.critical('クリティカル')


if __name__ == '__main__':
    # main()
    colorlog_sandbox()
