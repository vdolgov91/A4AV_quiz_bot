import datetime
import freezegun

import config
import dbOperations
import quizAggregator

import pytest
from pathlib import Path

import requests
import os, sys
from urllib.request import url2pathname

class LocalFileAdapter(requests.adapters.BaseAdapter):
    """Позволяет делать запрос с помощь requests в локальный html-файл
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
    '''Создать единую для всех тестов dbOperations папку в которой создастся файл БД ./app_db/a4av.db'''
    tmp_dir = tmp_path_factory.mktemp('tmp')
    return tmp_dir


@pytest.fixture(scope='session')
@freezegun.freeze_time("2023-12-13") # в качестве datetime.now() устанавливаем дату сохранения локальных HTML файлов
def quiz_from_local_files():
    '''Создаёт адаптеры для подключения модуля requests к локальным файлам html.
    В папке /test/saved_web_pages хранятся html-страницы с расписанием игр разных организаторов.
    Функция возвращает tulpe с содержимым (games, organizatorErrors), извлеченным из локальных файлов.
    '''
    responsesDict = {}
    cityOrganizators = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз',
                        'WOW Quiz/ Эйнштейн Party']
    cityLinks = ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk',
                 'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']

    organizatorsLinksLocal = {
    'Квиз Плиз': 'quizplease_schedule_2023-12-14.html',
    'Лига Индиго': 'ligaindigo_schedule_2023-12-14.html',
    'Мама Квиз': 'mamaquiz_schedule_2023-12-14.html',
    'WOW Quiz/ Эйнштейн Party': 'wowquiz_schedule_2023-12-20.html'
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
    games, organizatorErrors = quizAggregator.collectQuizData(cityOrganizators, cityLinks, responsesDict)
    return games, organizatorErrors

@pytest.fixture(scope='session')
def quiz_from_real_web_sites():
    '''Запрашиваем инфорамцию по квизам с настоящих веб сайтов на время фактического запуска теста'''
    cityOrganizatorsReal = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз',
                        'WOW Quiz/ Эйнштейн Party']
    cityLinksReal = ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk',
                 'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']
    gamesReal, organizatorErrorsReal = quizAggregator.collectQuizData(cityOrganizatorsReal, cityLinksReal)
    return gamesReal, organizatorErrorsReal

@pytest.fixture(scope='session')
def expected_games():
    '''Словарь заведомо корректных игр на основании запроса от 2023-12-13 в файлы
    ligaindigo_schedule_2023-12-14.html - 1
    mamaquiz_schedule_2023-12-14.html - 5 (одна 13 декабря, поэтому дату задаем 13.12)
    quizplease_schedule_2023-12-14.html - 3 (остальные резерв и должны быть отброшены)
    wowquiz_schedule_2023-12-20.html - 6 (остальные резерв и должны быть отброшены)
    '''
    return {
        'qp0': {'game': 'Квиз, плиз! NSK #567', 'date': datetime.datetime(2023, 12, 14, 20, 0), 'bar': 'Арт П.А.Б.',
                'tag': ['Классика']},
        'qp4': {'game': 'Квиз, плиз! NSK #569', 'date': datetime.datetime(2023, 12, 19, 20, 0), 'bar': 'Арт П.А.Б.',
                'tag': ['Классика']},
        'qp6': {'game': 'Квиз, плиз! NSK #570', 'date': datetime.datetime(2023, 12, 21, 20, 0), 'bar': 'Арт П.А.Б.',
                'tag': ['Классика']},
        'li0': {'game': 'Новый год СССР', 'date': datetime.datetime(2023, 12, 18, 19, 30), 'bar': 'Три Лося',
                'tag': ['Ностальгия']},
        'wow5': {'game': 'Обо всём. Похмельно-новогодняя #47 ', 'date': datetime.datetime(2024, 1, 2, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Классика']},
        'wow6': {'game': 'Угадай мелодию. Русское (туры по жанрам)', 'date': datetime.datetime(2024, 1, 3, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа']},
        'wow7': {'game': 'Топовые кино, мультфильмы, сериалы #4', 'date': datetime.datetime(2024, 1, 4, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа']},
        'wow8': {'game': 'Советское кино #2 (туры по 5 фильмам)', 'date': datetime.datetime(2024, 1, 5, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа']},
        'wow9': {'game': 'РУсская музыка 90-х и 00-х #2', 'date': datetime.datetime(2024, 1, 6, 16, 0),
                 'bar': 'Три Лося', 'tag': ['Мультимедиа', 'Ностальгия']},
        'wow10': {'game': 'Гарри Поттер лайт #29 (с туром про рождество)', 'date': datetime.datetime(2024, 1, 7, 16, 0),
                  'bar': 'Три Лося', 'tag': ['Мультимедиа']},
        'mama0': {'game': 'КВИЗАНУТЫЙ НОВЫЙ ГОД 2024', 'date': datetime.datetime(2023, 12, 13, 19, 30),
                  'bar': 'MISHKIN&MISHKIN', 'tag': []},
        'mama1': {'game': 'АЛКОКВИЗ #2', 'date': datetime.datetime(2024, 1, 3, 14, 0), 'bar': 'MISHKIN&MISHKIN',
                  'tag': []},
        'mama2': {'game': 'КИНОМЬЮЗИК: НОВОГОДНИЙ #2', 'date': datetime.datetime(2024, 1, 4, 14, 0),
                  'bar': 'MISHKIN&MISHKIN', 'tag': ['Мультимедиа']},
        'mama3': {'game': 'ЛОГИКА ГДЕ? #14', 'date': datetime.datetime(2024, 1, 5, 14, 0), 'bar': 'MISHKIN&MISHKIN',
                  'tag': []},
        'mama4': {'game': 'КЛАССИКА #128', 'date': datetime.datetime(2024, 1, 6, 14, 0), 'bar': 'MISHKIN&MISHKIN',
                  'tag': ['Классика']}
    }

