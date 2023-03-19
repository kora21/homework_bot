import exceptions
import logging
import os
import requests
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telegram import TelegramError

from exceptions import ApiStatusError, ApiAnswerError

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

RESPONSE_NOT_DICT = 'Ответ API не является словарем'
HOMEWORKS_NOT_IN_RESPONSE = 'Отсутствует ключ homeworks'
HOMEWORKS_NOT_LIST = 'Структура данных не соответсвует ожиданиям'


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)


def check_tokens():
    """Проверяем доступность переменных окружения."""
    tokens = (all)
    for token, value in tokens.items():
        if value is None:
            logger.error(f'{token} not found')
    return all(tokens.values())


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено: {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка отправки сообщения: {error}')
        raise TelegramError(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к API и получение ответа в формате JSON."""
    request_params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=request_params,
        )
        if response.status_code != HTTPStatus.OK:
            raise ApiStatusError(
                f'wrong HTTP status: {response.status_code}'
            )
        return response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ApiAnswerError(
            f'unexpected Api answer {error}'
        )
    except requests.exceptions.RequestException as error:
        raise ApiAnswerError(
            f'unexpected Api answer {error}'
        )


def check_response(response):
    """Проверка полученных данных."""
    if not isinstance(response['homeworks'], list):
        raise TypeError(RESPONSE_NOT_DICT)
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_NOT_IN_RESPONSE)
    homeworks = response['homeworks']
    if type(homeworks) is not list:
        raise TypeError(HOMEWORKS_NOT_LIST)
    return response.get('homeworks')


def parse_status(homework):
    """Отправка статуса проверки."""
    homework_name = homework["homework_name"]
    homework_status = homework["status"]
    if 'homework_name' not in homework:
        raise KeyError
    if 'status' not in homework:
        raise KeyError
    if homework_status not in HOMEWORK_VERDICTS or None:
        raise Exception
    verdict = HOMEWORK_VERDICTS[homework_status]
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
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
