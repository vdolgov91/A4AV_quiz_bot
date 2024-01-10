""""
Модуль конфигурации бота.
Здесь настраивается логирование, путь для подключения к базе данных, задается список тематик квизов,
указываются ссылки на сайты организаторов, указывается информация об организаторах по каждому конкретному городу.

Константы, используемые в других модулях:
    BOT_TOKEN (str) - токен для подключения к боту, импортируется из secrets.py (файл исключен из GIT)
    CITY_DICT (dict) - информация о городах, которые поддерживает бот
    DBPATH (str) - строка подключения к БД для SQLAlchemy
    logger - объект класса logger, с помощью которого ведется логирование
    ORGANIZATORS_DICT (dict) - информация об организаторах, с сайтов которых бот может получить информацию о квизах
    QUIZ_THEMES (dict) - перечень возможных тематик, которые присваиваются квизам и по к-ым можно фильтровать
    ROOT_DIR (pathlib.Path) - путь до корневого каталога проекта
    THEME_MAPPING_DICT - словарь для определения тематики квиза по словам, входящим в его название

Для заведения нового организатора, который проводит игры в разных городах:
* добавь его название, тэг и baseUrl в ORGANIZATORS_DICT
* добавь его во все города присутствия в словарь CITY_DICT
* если у него есть исключения при формировании итогового URL, то пропиши их в quizAggregator.create_info_by_city()
* добавь в quizAggregator.collectQuizData() функцию для скрейпинга HTML-страницы с расписанием игр
* пополни словарь THEME_MAPPING_DICT специфическими названиями игр организатора, чтобы корректно определять тематику
* если тематику сложно определить с помощью словаря, то добавь regexp или другую логику в
quizAggregator.assign_themes_to_quiz()
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

from secrets import BOT_TOKEN

# строка подключения к БД для SQLAlchemy
# на настоящий момент используется СУБД SQLite, поэтому указывается путь до файла
# выход в родительский каталог сделан потому что создание БД запускается из ./src/dbOperations.py,
# а база данных должна быть создана в ./app_db
DBPATH = 'sqlite:///../app_db/a4av.db'

# путь до корневого каталога проекта
curFileLocation = os.path.abspath(__file__)   # D:\Python\userdir\A4AV_quiz_bot\src\config.py
curFileDir = os.path.dirname(curFileLocation) # D:\Python\userdir\A4AV_quiz_bot\src
rootDir = os.path.dirname(curFileDir)         # D:\Python\userdir\A4AV_quiz_bot
ROOT_DIR = Path(rootDir)                      # path object

# настройки логирования
# https://stackoverflow.com/questions/57204920/how-to-properly-format-the-python-logging-formatter
if not os.path.exists(ROOT_DIR / 'logs'):
    os.mkdir(ROOT_DIR / 'logs')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler =  RotatingFileHandler(filename=ROOT_DIR / 'logs/a4av_bot_{:%Y-%m-%d}.log'.format(datetime.now()), maxBytes=10000000, backupCount=10)
handler.setFormatter(logFormatter)
logger.addHandler(handler)

# тематики задаются в одном месте для всех городов. из них автоматически формируются клавиатура при выборе тематики игры
# и позиции опроса при добавлении исключений. При добавлении тематики не забудьте добавить ее в src/telegramBot.py:
# THEME: [MessageHandler(filters.Regex("^(Оставить все|Классика|Мультимедиа|Ностальгия|18+)$"), sendquiz_filtered),
QUIZ_THEMES = ['Оставить все', 'Классика', 'Мультимедиа', 'Ностальгия', '18+', 'Новички']

# словарь для определения тематики квиза по словам, входящим в его название
# у Лиги Индиго дополнительно используются regexp-ы для определения классики в формате '10 игра 4 сезона'
# названия категорий пишем с Заглавной, все тэги внутри категории - строчными
THEME_MAPPING_DICT = {
    'Классика': ['квиз, плиз! nsk','железные яйца','блиц','классика','обо всём','fun','эйнштейн party','новички'],
    'Мультимедиа': ['музыка','кино','шазам','сериал','мультфильм','мультик','гарри поттер','мелоди','друзья','аниме',
                    'властелин колец','игра престолов','клиника','сумерки','indigo show','music','литература','футбол',
                    'компьютерн','видео','марвел','мстител','marvel', 'спорт'],
    'Новички': ['новички'],
    'Ностальгия': ['ссср', '00-', '90-', '80-', 'советск'],
    '18+': ['18+', 'чёрный квиз', 'черный квиз']
}

# словарь для организаторов, которые проводят квизы во многих городах
# присваивиаем организаторам короктие тэги, которые будет использоваться при фильтрации под предпочтения пользователя
# в качестве ключа словаря пишем название организатора, в качестве значения на 0 позиции - тэг организатора,
# на 1 позиции - ссылку, где строкой <city_tag> указывается в каком месте ссылка параметризируется
ORGANIZATORS_DICT = {
    'Квиз Плиз': ['qp','https://<city_tag>.quizplease.ru/schedule'],                # https://nsk.quizplease.ru/schedule
    'Лига Индиго': ['li','https://ligaindigo.ru/<city_tag>'],                       # https://ligaindigo.ru/novosibirsk
    'Мама Квиз': ['mama','https://<city_tag>.mamaquiz.ru/'],                        # https://nchk.mamaquiz.ru/, у Новосибирска просто https://mamaquiz.ru/
    'WOW Quiz/ Эйнштейн Party': ['wow','https://<city_tag>.wowquiz.ru/schedule']    # https://nsk.wowquiz.ru/schedule
}

# словарь с информацией о городах - какие организаторы есть, какой у этого организатора <city_tag> для формирования
# ссылки на страницу с расписанием, на каких площадках проводят игры,
# правила заполнения словаря: тэги должны совпадать с organizatorsTags;
# если организатора нет в городе, его тэг не добавляем.
# все возможные ключи словаря должны быть добавлены в Образец заполнения с комментарием
CITY_DICT = {
    'Образец Заполнения': {                 # название города
        'bars': ['Red Lion', 'Хамовники'],  # названия баров, где проводятся квизы
        'qp': 'msc',                        # обозначение города в URL организатора "Квиз Плиз", например, nsk
        'li': 'moscow',                     # обозначение города в URL организатора "Лига Индиго", например, Novosibirsk
        'mama': 'tomsk',                    # обозначение города в URL организатора "Мама Квиз", например, tomsk
        'wow': 'msc',                       # обозначение города в URL организатора "WOW Quiz/ Эйнштейн Party", например, nsk
        'local_organizators': [             # информация о местных организаторах, name - название организатора, link - ссылка на страницу с расписанием квизов
            {'name': 'ТестКвиз', 'link': 'https://don.testquiz.link/schedule'},
            {'name': 'Quiz Club Test', 'link': 'https://quizclub.link/don/schedule'}
        ]
    },
    'Новосибирск': {
        'bars': ['Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки ВВерх!'],
        'qp': 'nsk',
        'li': 'novosibirsk',
        'mama': 'nsk',
        'wow': 'nsk',
        'local_organizators': []
    },

}
