import exceptions
import logging
import os
import requests
import telegram
import time

from dotenv import load_dotenv
from exceptions import ApiStatusError, ApiAnswerError
from http import HTTPStatus
from telegram import TelegramError


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


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)


def check_tokens():
    """Проверяем доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено: {message}')
    except TelegramError as error:
        logger.error(f'Ошибка отправки сообщения: {error}')
    else:
        logger.debug(f'Сообщение отправлено: {message}')


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
    if not isinstance(response, dict):
        raise TypeError('Структура данных не является словарем')
    if 'homeworks' not in response:
        raise TypeError('Отсутствует ключ homeworks')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Структура данных не является списком')
    return response.get('homeworks')


def parse_status(homework):
    """Отправка статуса проверки."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        raise KeyError('Нет ключа домашней работы')
    if status is None:
        raise KeyError('Отсудствует статус')
    if status not in HOMEWORK_VERDICTS or None:
        raise ValueError('Неверный статус домашней работы')
    verdict = HOMEWORK_VERDICTS[status]
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
            homeworks_status = check_response(response)
            if not homeworks_status:
                send_message(bot, 'Изменений нет')
                logger.debug('Изменений нет')
            else:
                new_message = parse_status(homeworks_status[0])
                send_message(bot, f'статус домашней работы '
                             f'обновлен - {new_message}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
