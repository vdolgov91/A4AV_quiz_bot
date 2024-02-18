"""
Fixtures-функции для тестирования с помощью pytest.

Содержит классы:
    LocalFileAdapter(requests.adapters.BaseAdapter)
Содержит функции:
    expected_games()
    expected_games_2()
    expected_games_mama_quiz()
    mama_quiz_from_local_files()
    quiz_from_real_web_sites()
    quiz_from_local_files()
    temp_db_path(tmp_path_factory)
"""

import datetime
import logging
import logging.config
import os
import sys
from pathlib import Path
from urllib.request import url2pathname

import freezegun
import pytest
import requests

# добавляем папку src в путь поиска, чтобы модули из этой папки можно было импортировать без указания их местонахождения
sys.path.insert(1, sys.path[0] + '/src')
import config
import dbOperations
import quizAggregator

# применяем глобальную конфигурацию логирования, операция должна быть выполнена при запуске приложения
logging.config.dictConfig(config.LOGGING_CONFIG)

class LocalFileAdapter(requests.adapters.BaseAdapter):
    """Позволяет делать запрос с помощь requests в локальный html-файл. Исходник:
    https://stackoverflow.com/questions/10123929/fetch-a-file-from-a-local-url-with-python-requests
    """

    @staticmethod
    def _chkpath(method, path):
        """Return an HTTP status for the given filesystem path."""
        if method.lower() in ('put', 'delete'):
            return 501, "Not Implemented"  # TODO
        elif method.lower() not in ('get', 'head'):
            return 405, "Method Not Allowed"
        elif os.path.isdir(path):
            return 400, "Path Not A File"
        elif not os.path.isfile(path):
            return 404, "File Not Found"
        elif not os.access(path, os.R_OK):
            return 403, "Access Denied"
        else:
            return 200, "OK"

    def send(self, req, **kwargs):  # pylint: disable=unused-argument
        """Return the file specified by the given request"""
        path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
        response = requests.Response()

        response.status_code, response.reason = self._chkpath(req.method, path)
        if response.status_code == 200 and req.method.lower() != 'head':
            try:
                response.raw = open(path, 'rb')
            except (OSError, IOError) as err:
                response.status_code = 500
                response.reason = str(err)

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        response.request = req
        response.connection = self

        return response

    def close(self):
        pass


@pytest.fixture(scope='session')
def temp_db_path(tmp_path_factory):
    """Создать единую для всех тестов dbOperations папку в которой создастся файл БД ./app_db/a4av.db"""
    tmp_dir = tmp_path_factory.mktemp('tmp')
    return tmp_dir


@pytest.fixture(scope='session')
@freezegun.freeze_time("2023-12-13")  # в качестве datetime.now() устанавливаем дату сохранения локальных HTML файлов
def quiz_from_local_files():
    """Создаёт адаптеры для подключения модуля requests к локальным копиям веб-страниц.
    В папке /test/saved_web_pages хранятся html-страницы с расписанием игр разных организаторов.
    Функция возвращает tulpe с содержимым (games, organizatorErrors), извлеченным из локальных файлов.
    """
    responsesDict = {}
    cityOrganizators = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Эйнштейн пати',
                        'WOW Quiz']
    cityLinks = ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk',
                 'https://nsk.albertparty.ru/schedule', 'https://nsk.wowquiz.ru/schedule']

    organizatorsLinksLocal = {
    'Квиз Плиз': 'quizplease_schedule_2023-12-14.html',
    'Лига Индиго': 'ligaindigo_schedule_2023-12-14.html',
    'Эйнштейн пати': 'einstein_party_schedule_2024-01-19.html',
    'WOW Quiz': 'wowquiz_schedule_2023-12-20.html'
}
    for key, value in organizatorsLinksLocal.items():
        # формируем ссылку на нужный HTML-файл сначала в формате Path, потом конвертируем в URI
        pathToLocalHTML = config.ROOT_DIR / 'tests/saved_web_pages' / value
        if os.path.exists(pathToLocalHTML):
            localURI = pathToLocalHTML.as_uri()
            # создаем сессию до локального файла с помощью кастомного адаптера LocalFileAdapter
            requests_session = requests.session()
            requests_session.mount('file://', LocalFileAdapter())
            response = requests_session.get(f'file://{localURI}')
            responsesDict[key] = response
        else:
            raise FileExistsError(f'File {pathToLocalHTML} does not exist')
    games, organizatorErrors = quizAggregator.collect_quiz_data(cityOrganizators, cityLinks, responsesDict)
    return games, organizatorErrors


@pytest.fixture(scope='session')
def quiz_from_real_web_sites():
    """Запрашиваем инфорамцию по квизам с настоящих веб сайтов на время фактического запуска теста"""
    cityOrganizatorsReal = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз',
                        'WOW Quiz']
    cityLinksReal = ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk',
                 'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']
    gamesReal, organizatorErrorsReal = quizAggregator.collect_quiz_data(cityOrganizatorsReal, cityLinksReal)
    return gamesReal, organizatorErrorsReal


@pytest.fixture(scope='session')
def expected_games():
    """Словарь заведомо корректных игр на основании запроса от 2023-12-13 в файлы
    einstein_party_schedule_2024-01-19.html - 2 (1 в резерве)
    ligaindigo_schedule_2023-12-14.html - 1
    mamaquiz_schedule_2023-12-14.html - 5 (одна 13 декабря, поэтому дату задаем 13.12)
    quizplease_schedule_2023-12-14.html - 3 (остальные резерв и должны быть отброшены)
    wowquiz_schedule_2023-12-20.html - 6 (остальные резерв и должны быть отброшены)
    Порядок организаторов должен быть в том же порядке, в каком организаторы указаны в config.ORGANIZATORS_DICT
    """
    return {
        'qp0': {'game': 'Квиз, плиз! NSK #567', 'date': datetime.datetime(2023, 12, 14, 20, 0), 'bar': 'Арт П.А.Б.',
                'tag': ['Классика']},
        'qp4': {'game': 'Квиз, плиз! NSK #569', 'date': datetime.datetime(2023, 12, 19, 20, 0), 'bar': 'Арт П.А.Б.',
                'tag': ['Классика']},
        'qp6': {'game': 'Квиз, плиз! NSK #570', 'date': datetime.datetime(2023, 12, 21, 20, 0), 'bar': 'Арт П.А.Б.',
                'tag': ['Классика']},
        'li0': {'game': 'Новый год СССР', 'date': datetime.datetime(2023, 12, 18, 19, 30), 'bar': 'Три Лося',
                'tag': ['Ностальгия']},
        'ein2': {'game': 'Кино', 'date': datetime.datetime(2024, 1, 23, 19, 30), 'bar': 'Типография',
                 'tag': ['Мультимедиа']},
        'ein3': {'game': 'Нулевые (00е)', 'date': datetime.datetime(2024, 1, 28, 16, 0), 'bar': 'Типография',
                 'tag': ['Ностальгия']},
        'wow5': {'game': 'Обо всём. Похмельно-новогодняя #47 ', 'date': datetime.datetime(2024, 1, 2, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Классика']},
        'wow6': {'game': 'Угадай мелодию. Русское (туры по жанрам)', 'date': datetime.datetime(2024, 1, 3, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа']},
        'wow7': {'game': 'Топовые кино, мультфильмы, сериалы #4', 'date': datetime.datetime(2024, 1, 4, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа']},
        'wow8': {'game': 'Советское кино #2 (туры по 5 фильмам)', 'date': datetime.datetime(2024, 1, 5, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа', 'Ностальгия']},
        'wow9': {'game': 'РУсская музыка 90-х и 00-х #2', 'date': datetime.datetime(2024, 1, 6, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа', 'Ностальгия']},
        'wow10': {'game': 'Гарри Поттер лайт #29 (с туром про рождество)', 'date': datetime.datetime(2024, 1, 7, 16, 0),
                  'bar': 'Три Лося', 'tag': ['Мультимедиа']}
    }


@pytest.fixture(scope='session')
def expected_games_2():
    """Словарь заведомо корректных игр на основании старого настоящего запроса через заведомо рабочую версию бота.
    Нужен для работы с тэгами '18+' и 'Новички', так как игр подходящих под такие тэги нет в сохраненных HTML-файлах.
    Порядок организаторов должен быть в том же порядке, в каком организаторы указаны в config.ORGANIZATORS_DICT
    """
    return {
'qp0': {'game': 'Квиз, плиз! NSK #458', 'date': datetime.datetime(2023, 1, 25, 20, 0), 'bar': 'Типография',
        'tag': ['Классика']},
'qp2': {'game': 'Квиз, плиз! [железные яйца] NSK #5', 'date': datetime.datetime(2023, 1, 26, 20, 0),
        'bar': 'Руки ВВерх!', 'tag': ['Классика']},
'qp4': {'game': '[новички] NSK #459', 'date': datetime.datetime(2023, 1, 28, 16, 0), 'bar': 'Максимилианс',
        'tag': ['Классика', 'Новички']},
'qp5': {'game': '[новички] NSK #459', 'date': datetime.datetime(2023, 1, 29, 16, 0), 'bar': 'Арт П.А.Б.',
        'tag': ['Классика', 'Новички']},
'qp6': {'game': '[кино и музыка] NSK #93', 'date': datetime.datetime(2023, 1, 29, 18, 0), 'bar': 'Максимилианс',
        'tag': ['Мультимедиа']},
'qp7': {'game': '[литература] NSK #3', 'date': datetime.datetime(2023, 1, 31, 20, 0), 'bar': 'Арт П.А.Б.',
        'tag': ['Мультимедиа']},
'li0': {'game': 'Игра №3 Сезон №7', 'date': datetime.datetime(2023, 1, 30, 19, 30), 'bar': 'Три Лося',
        'tag': ['Классика']},
'wow2': {'game': 'СССР vs 90ые!', 'date': datetime.datetime(2023, 1, 28, 16, 0), 'bar': 'Три Лося',
         'tag': ['Ностальгия']},
'wow3': {'game': 'Черный квиз 18+ #2', 'date': datetime.datetime(2023, 1, 29, 18, 0), 'bar': 'Три Лося',
         'tag': ['18+']},
'wow17': {'game': '18+ #16 За гранью приличия', 'date': datetime.datetime(2023, 2, 19, 18, 0), 'bar': 'Три Лося',
          'tag': ['18+']}
}


