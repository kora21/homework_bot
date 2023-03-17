import logging
import os
import time
# import json
# import sys
import requests
# from datetime import datetime
import telegram
from http import HTTPStatus

from dotenv import load_dotenv
import exceptions

# from exceptions import (ResponseError, StatusCodeError, TokenError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

SEND_MESSAGE_ERROR = 'Ошибка при отправке сообщения: {}'
RESPONSE_NOT_DICT = 'Ответ API не является словарем'
HOMEWORKS_NOT_IN_RESPONSE = 'Отсутствует ключ homeworks'
HOMEWORKS_NOT_LIST = 'Структура данных не соответсвует ожиданиям'
STATUS_CODE_ERROR = ('Ошибка при запросе к API: '
                     'status_code: {status_code}, endpoint: {url}, '
                     'headers: {headers}, params: {params}')
LOG_DEBUG_ENDPOINT_QUERY = 'Запрос информации с эндпойнта "{url}"'
LOG_DEBUG_ENDPOINT_ERROR_QUERY = ('Эндпоинт "{url}" недоступен.'
                                  'Код ответа: "{status_code}"')


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)


def check_tokens():
    """Проверяем доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN}
    for token, value in tokens.items():
        if value is None:
            logger.error(f'{token} not found')
    return all(tokens.values())


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено: {message}')
    except Exception as error:
        logging.error(error, exc_info=True)


def get_api_answer(timestamp):
    """Запрос к API и получение ответа в формате JSON."""
    request_params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, params=request_params,
        )
    except exceptions.APIResponseStatusCodeException:
        logger.error('Сбой при запросе к эндпоинту')
    if response.status_code != HTTPStatus.OK:
        msg = 'Сбой при запросе к эндпоинту'
        raise exceptions.APIResponseStatusCodeException(msg)
    return response.json()


def check_response(response):
    """Проверка полученных данных."""
    if type(response) is not dict:
        raise TypeError(RESPONSE_NOT_DICT)
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_NOT_IN_RESPONSE)
    homeworks = response['homeworks']
    if type(homeworks) is not list:
        raise TypeError(HOMEWORKS_NOT_LIST)
    return response.get('homeworks')


def parse_status(homework):
    """Отправка статуса проверки."""
    if (not isinstance(homework, dict)
            or 'status' not in homework
            or homework.get('status') not in HOMEWORK_VERDICTS):
        logging.error(TypeError)
        raise TypeError
    if 'homework_name' not in homework:
        logging.error(TypeError)
        raise TypeError
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсудствует переменная окружения'
        logger.critical(message)
        raise exceptions.TokenError
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, 'Привет, я начал работу')
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', int(time.time()))
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            try:
                bot.send_message(TELEGRAM_CHAT_ID, message)
            except Exception as error:
                logging.exception(SEND_MESSAGE_ERROR.format(error))
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
