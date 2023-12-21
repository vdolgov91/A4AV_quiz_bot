import datetime
import freezegun

import config
import dbOperations

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
    import quizAggregator
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

