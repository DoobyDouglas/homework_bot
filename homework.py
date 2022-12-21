import os
import sys
import logging
import telegram
import requests
import time

from dotenv import load_dotenv
from json.decoder import JSONDecodeError


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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

type_error = 'Ошибка типа данных'
api_key_error = 'Ключа нет в ответе от API'
no_status = 'Отсутствие статуса'
strange_status = 'Неожиданный статус домашней работы'
main_error = 'Сбой в работе программы: '


def check_tokens():
    """Проверяет наличие токенов."""
    required_variables = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    for key, value in required_variables.items():
        if value is None:
            logger.critical(f'{key} отсутствует')
            raise SystemExit


def send_message(bot, message):
    """Отправляет сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        print(logger.error)


def get_api_answer(timestamp):
    """Получает ответ от API."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if homework_statuses.status_code != 200:
            homework_statuses.raise_for_status()
    except requests.exceptions.RequestException:
        logger.error('Ошибка запроса')

    try:
        response = homework_statuses.json()
    except JSONDecodeError:
        logger.error(type_error)
    return response


def check_response(response):
    """Проверяет ответ от API."""
    if isinstance(response, dict):
        if 'homeworks' not in response:
            logger.error(api_key_error)
            raise KeyError(api_key_error)
        if not isinstance(response['homeworks'], list):
            raise TypeError(type_error)
    homework = response['homeworks']
    return homework


def parse_status(homework):
    """Проверяет статус домашней работы."""
    if 'homework_name' not in homework:
        logger.error(api_key_error)
        raise KeyError(api_key_error)
    homework_name = homework['homework_name']
    status = homework['status']
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
    elif status is None:
        logger.error(no_status)
        raise Exception(no_status)
    else:
        logger.error(strange_status)
        raise Exception(strange_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                message = parse_status(
                    response.get('homeworks')[0]
                )
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'{main_error}{error}'
            logger.error(f'{main_error}{error}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
