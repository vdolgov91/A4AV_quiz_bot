import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import os
from secrets import botToken

# строка подключения к файлу БД
# выход в родительский каталог сделан потому что создание БД запускается из ./src/dbOperations.py
# а каталог должен быть создан в ./app_db
dbPath = 'sqlite:///../app_db/a4av.db'

curFileLocation = os.path.abspath(__file__)   # D:\Python\userdir\A4AV_quiz_bot\src\config.py
curFileDir = os.path.dirname(curFileLocation) # D:\Python\userdir\A4AV_quiz_bot\src
rootDir = os.path.dirname(curFileDir)         # D:\Python\userdir\A4AV_quiz_bot
ROOT_DIR = Path(rootDir)                      # path object


# https://stackoverflow.com/questions/57204920/how-to-properly-format-the-python-logging-formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler =  RotatingFileHandler(filename=ROOT_DIR / 'logs/a4av_bot_{:%Y-%m-%d}.log'.format(datetime.now()), maxBytes=10000000, backupCount=10)
handler.setFormatter(logFormatter)
logger.addHandler(handler)


# тематики задаются в одном месте для всех городов. из них автоматически формируются клавиатура при выборе тематики игры и позиции опроса при добавлении исключений
# при добавлении тематики не забудьте добавить ее в
# telegramBot.py> THEME: [MessageHandler(filters.Regex("^(Оставить все|Классика|Мультимедиа|Ностальгия|18+)$"), sendquiz_filtered),
themes = ['Оставить все','Классика','Мультимедиа','Ностальгия','18+','Новички']

# словарь для определения тематики квиза по его названию
#у Лиги Индиго еще есть регекспы для определения классики в формате 10 игра 4 сезона

#названия категорий пишем с Заглавной, все тэги внутри категории - строчными
themeMappingDict = {
    'Классика': ['квиз, плиз! nsk','железные яйца','блиц','классика','обо всём','fun','эйнштейн party','новички'],
    'Мультимедиа': ['музыка','кино','шазам','сериал','мультфильм','мультик','гарри поттер','мелоди','друзья','аниме','властелин колец','игра престолов','клиника','сумерки','indigo show','music','литература','футбол','компьютерн','видео','марвел','мстител','marvel', 'спорт'],
    'Новички': ['новички'],
    'Ностальгия': ['ссср', '00-', '90-', '80-', 'советск'],
    '18+': ['18+', 'чёрный квиз', 'черный квиз']
}

#для заведения нового организатора, который проводит игры в разных городах:
# * добавь его название, тэг и baseUrl в organizatorsDict
# * добавь его во все города присутствия в словарь cityDict
# * если у него есть исключения при формировании итогового URL, то пропиши их в quizAggregator.createInfoByCity()
# * добавь в quizAggregator.collectQuizData код для парсинга HTML-страницы с расписанием игр
# * пополни словарь themeMappingDict специфическими названиями игр организатора, чтобы корректно определять тематику
# * если тематику сложно определить с помощью словаря, то добавь regexp или другую логику в quizAggregator.assignThemesToQuiz()

#сюда добавляем соответствие названия организатора его тэгу, который будет использоваться при фильтрации под предпочтения пользователя
#в качестве ключа словаря пишем название организатора, в качестве значения на 0 позиции - тэг организатора, на 1 позиции - ссылку, где строкой <city_tag> указывается в каком месте ссылка параметризируется
organizatorsDict = {
    'Квиз Плиз': ['qp','https://<city_tag>.quizplease.ru/schedule'],                # https://nsk.quizplease.ru/schedule
    'Лига Индиго': ['li','https://ligaindigo.ru/<city_tag>'],                       # https://ligaindigo.ru/novosibirsk
    'Мама Квиз': ['mama','https://<city_tag>.mamaquiz.ru/'],                        # https://nchk.mamaquiz.ru/, у Новосибирска просто https://mamaquiz.ru/
    'WOW Quiz/ Эйнштейн Party': ['wow','https://<city_tag>.wowquiz.ru/schedule']    # https://nsk.wowquiz.ru/schedule
}

#правила заполнения словаря: тэги должны совпадать с organizatorsTags; если организатора нет в городе, его тэг не добавляем
#все возможные ключи словаря должны быть добавлены в Образец заполнения с комментарием
cityDict = {
    'Образец Заполнения': {                 # название города
        'bars': ['Red Lion', 'Хамовники'],  # названия баров, где проводятся квизы
        'qp': 'msc',               # обозначение города в URL организатора "Квиз Плиз", например, nsk
        'li': 'moscow',      # обозначение города в URL организатора "Лига Индиго", например, Novosibirsk
        'mama': 'tomsk',           # обозначение города в URL организатора "Мама Квиз", например, tomsk
        'wow': 'msc',              # обозначение города в URL организатора "WOW Quiz/ Эйнштейн Party", например, nsk
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
