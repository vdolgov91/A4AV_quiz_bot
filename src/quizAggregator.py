"""
Модуль скрэйпинга информации о квизах с сайтов организаторов и форматировании её под требования телеграм-бота.

Содержит функции:
    assign_themes_to_quiz(gamename, organizator) - присваивает каждому квизу список тематик
    collect_quiz_data(cityOrganizators, cityLinks, localHTMLs=None) - собирает информацию о проводящихся в городе квизах
    create_formatted_quiz_list(games, organizatorErrors, **kwargs) - создает итоговый список квизов для telegramBot.py
    create_info_by_city(city) - формирует информацию об организаторах, барах, ссылках на сайты для конкретного города
    get_data_from_web_page(orgName, orgLink, localHTMLs) - делает веб-запрос страницы организатора с расписанием квизов
    scrape_liga_indigo(quizSoup, orgName, orgTag, dateParams, localHTMLs=None) - скрейпит информацию с сайта Лига Индиго
    scrape_mama_quiz(quizSoup, orgName, orgTag, dateParams) - скрейпит информацию с сайта Мама Квиз
    scrape_quiz_please(quizSoup, orgName, orgTag, dateParams) - скрейпит информацию с сайта Квиз Плиз
    scrape_wow_quiz(quizSoup, orgName, orgTag, dateParams) - - скрейпит информацию с сайта Wow Quiz

Содержит константы:
    DOW_DICT - словарь соответствия порядкового номера дня недели его названию (1: 'понедельник')
    MONTH_DICT - словарь соответствия названия месяца его порядковому номеру ('января': 1)
"""

import datetime
import logging
import re

import bs4
import requests

from config import (
    CITY_DICT,
    ORGANIZATORS_DICT,
    QUIZ_THEMES,
    THEME_MAPPING_DICT
)

# начать логирование в модуле
logger = logging.getLogger(__name__)

# указываем соответствия текстовых названий месяцов и дней недели (Days Of Week) цифрам, для преобразования
MONTH_DICT = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
              'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
DOW_DICT = {1: 'понедельник', 2: 'вторник', 3: 'среда', 4: 'четверг', 5: 'пятница', 6: 'суббота', 7: 'воскресенье'}

def create_info_by_city(city):
    """
    Формирует набор информации, индивидуальной для города проведения - организаторы, ссылки на их сайты, бары на
    основе информации из config.CITY_DICT и config.ORGANIZATORS_DICT. Приводит информацию в нужный для модуля
    telegramBot формат.
    На текущий момент работает только для Новосибирска, пользователь бота нигде не может задать другой город.

    :param city (str): Название города
    :return: tuple(cityBars (list), cityOrganizators (list), cityLinks (list))
    """
    if city not in CITY_DICT:
        logger.info(f'Информации по квизам, проводимым в городе {city} пока нет.')
        return [], [], []

    # задаем значения нулевых элементов формируемых list-ов
    # они необходимы при создании опроса по исключения из вывода пользователю игр определенных тематик и баров
    # для cityLinks такого значения нет, но мы добавляем placeholder, чтобы элементы этого листа соответстовали
    # элементам остальных двух
    cityBars = ['Оставить все бары']
    cityOrganizators = ['Оставить всех организаторов']
    cityLinks = ['placeholder']

    # формируем список баров в городе для создания опроса в формате
    # ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки вверх']
    cityBars += CITY_DICT[city]['bars']

    # добавляем в список cityOrganizators всех 'всероссийских' организаторов, присутствующих в городе
    # добавляем в список cityLinks ссылки на страницу с расписанием квизов этого организатора в этом городе
    for curOrg in ORGANIZATORS_DICT:
        curTag = ORGANIZATORS_DICT[curOrg][0]      # 'li'
        curBaseUrl = ORGANIZATORS_DICT[curOrg][1]  # 'https://ligaindigo.ru/<city_tag>'
        curCityTag = CITY_DICT[city].get(curTag)
        if curCityTag is not None:
            # заменяем плэйсхолдер <city_tag> на тэг конкретного города
            curLink = curBaseUrl.replace('<city_tag>', curCityTag)
            cityLinks.append(curLink)
            cityOrganizators.append(curOrg)

    # добавляем к списку 'всероссийских' организаторов местных организаторов
    # на настоящий момент функционал не используется, заготовка на будущее
    localOrgs = CITY_DICT[city].get('local_organizators')
    if localOrgs is not None:
        for curDict in localOrgs:
            link = curDict.get('link')
            name = curDict.get('name')
            # добавляем информацию по местным организаторам только если оба значения извлеклись корректно
            if link is not None and name is not None:
                cityLinks.append(link)
                cityOrganizators.append(name)
            else:
                logger.error(f'Не получилось извлечь название или ссылку на сайт местного организатора по городу '
                             f'{city}, вероятно ошибка в словаре в этой строке: {curDict}')
    logger.debug(f'По городу {city} сформированы списки баров: {cityBars}, организаторов: {cityOrganizators}, '
                 f'ссылок на сайты организаторов: {cityLinks}''')
    return cityBars, cityOrganizators, cityLinks

def assign_themes_to_quiz(gamename, organizator):
    """
    Присваивает квизу список соответствующих ему тематик. Тематики определяются согласно словарю
    config.THEME_MAPPING_DICT и уникальным правилам, описанным внутри этой функции.
    Например, 'Кино и музыка СССР #6' будут присвоены тематики ['Мультимедиа', 'Ностальгия'],
    '[новички] NSK #459' будут присвоены тематики ['Классика', 'Новички']

    :param gamename (str): название квиза
    :param organizator (str): название организатора, в формате как он указан в config.ORGANIZATORS_DICT
    :return: tags (list): список тематик квиза
    """
    # приводим название игры к строчному регистру для последующих проверок с помощью оператора in
    # одновременно проверяем корректность типа переменной gamename
    try:
        gamename = gamename.lower()
    except:
        logger.error(f'Некорректное значение gamename: {gamename}, должно быть значения типа string')
        return

    tags = []

    # доп. проверка для игр с названием вида 'Игра №2 Сезон №7' у Лиги Индиго
    # внимание, формат может периодически меняться
    if organizator == 'Лига Индиго':
        liGameNameRegEx = re.compile(r'^игра\s+№(\d+)\s+сезон.*')  # 'игра №2 сезон №7'
        mo = liGameNameRegEx.search(gamename)
        if mo != None:
            tags.append('Классика')

    for k in THEME_MAPPING_DICT:          # перебираем все тематики ('Классика')
         for j in THEME_MAPPING_DICT[k]:  # перебираем все тэги внутри тематики (['18+', 'чёрный квиз'])
             if j in gamename:            # j = тэг из словаря ('чёрный квиз')
                tags.append(k)
                break  # прекращаем проверять другие тэги внутри уже присвоенной тематики, переходим к следующему k
    return tags


def get_data_from_web_page(orgName, orgLink, localHTMLs):
    """Делает веб-запрос страницы с расписанием квиза данного организатора.
    Возвращает объект bs4.BeautifulSoup с HTML-кодом страницы для последующего скрейпинга.
    :param orgName (str): название организатора
    :param orgLink (str): ссылка на веб-страницу с расписанием квизов организатора в конкретном городе
    :param localHTMLs (dict): для unit-тестов, словарь в котором хранятся объекты requests.get с локальных копий
                              web-страниц. См. функцию tests/conftest.py/quiz_from_local_files()
    :return quizSoup (bs4.BeautifulSoup): объект с текстом HTML-кода страницы с расписанием квизов
    """

    # если скрейпим страницу Мама Квиз, нужно добавить в запрос HTTP-заголовк User-agent,
    # значение можно взять из своего браузера. без него вернет ошибку 403 Forbidden
    if orgName == 'Мама Квиз' and len(localHTMLs) == 0:
        userAgent = {'User-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'}
        res = requests.get(orgLink, headers=userAgent)
        res.raise_for_status()

    # если скрейпим настоящие web-страницы других организаторов
    elif len(localHTMLs) == 0:
        res = requests.get(orgLink)
        res.raise_for_status()

    # если работаем с локальными копиями web-страниц
    else:
        res = localHTMLs[orgName]

    return bs4.BeautifulSoup(res.text, 'html.parser')


def scrape_liga_indigo(quizSoup, orgName, orgTag, dateParams, localHTMLs=None):
    """
    Функция которая скрейпит информацию с сайта Лига Индиго и возвращает список квизов и возникших ошибок.
    :param quizSoup (bs4.BeautifulSoup): объект с HTML-кодом страницы с расписанием квизов
    :param orgName (str): имя организатора ('Лига Индиго')
    :param orgTag (str): тэг организатора ('li')
    :param dateParams (list): список временных параметров из collect_quiz_data
    :param localHTMLs (dict): для unit-тестов, словарь в котором хранятся объекты requests.get с локальных копий
                              web-страниц. Для локальной копии страницы ЛИ используется другой CSS-селектор.
    :return: games (dict), organizatorErrors (dict)
    """
    games = {}
    organizatorErrors = {}
    curYear, nextYear, curMonth, curDT = dateParams

    # нельзя использовать mutable объекты в качестве дефолтных значений параметров функции
    # так как нам нужен localHTMLs типа dict, то переопределяем его
    if localHTMLs is None:
        localHTMLs = {}

    try:
        # по CSS-селектору нужного HTML-элемента, скопированному из браузера, bs4 ничего не находит
        # поэтому извлекаем общий родительский элемент нужных элементов и далее ищем в нем вручную.
        # для локальной копии веб-страницы CSS-селектор почему-то отличается от селектора для реальной страницы,
        # поэтому если на вход функции из unit-тестов был передан localHTMLs, то используем селектор для локальной копии
        if len(localHTMLs) == 0:
            liGamesList = quizSoup.select('#info > div > div > div')  # для настоящего сайта
        else:
            liGamesList = quizSoup.select('#info > div > div > div > div > div > div > div')  # для локальной копии

        # основная информация о квизах содержится в 0, 1, 2 дочерних элементах элемента liGamesList, поэтому цикл
        # по нему идет с шагом i + 3.
        # информация о наличии мест на игру лежит в 0,2,4... дочерних элементах отдельного элемента liGamesAvailable,
        # поэтому эту информацию извлекаем из этого элемента с отдельным счётчиком с шагом k + 2
        liGamesAvailable = quizSoup.select(r'#info > div > div')
        k = 0

        for i in range(0, len(liGamesList), 3):
            # извлекаем название квиза вида "10 игра 4 сезона", они хранятся в 0, 3, 6 и т.д дочерних элементах
            liGameName = liGamesList[i].text
            # по названию игры добаляем тэг с тематикой, для Лиги Индиго есть дополнительные правила присвоения тэгов
            liGameTag = assign_themes_to_quiz(liGameName, orgName)

            # извлекаем дату проведения в виде "13 Июня 2022 в 19:30", она хранится в 1, 4, 7 дочерних элементах
            liDateTime = liGamesList[i + 1].text
            # преобразовываем дату проведения квиза в нужный формат
            liDateRegEx = re.compile(r'''
                                       ^(\d|\d\d)\s         # одна или две цифры в начале строки, после пробел
                                       ([А-Яа-я]+)\s        # месяц, после него запятая пробел
                                       (\d{4}).*            # год и любые символы
                                       (\d\d):(\d\d)$       # часы:минуты
                                       ''', re.VERBOSE)
            mo = liDateRegEx.search(liDateTime)
            liDay, liMonth, liYear, liHour, liMinute = mo.groups()
            # преобразуем текстовое название месяца в цифру с помощью словаря MONTH_DICT
            liMonth = MONTH_DICT[liMonth.lower()]
            # у Лиги Индиго указан год проведения квиза, поэтому дата всегда формируется правильно без доп. действий
            quizDT = datetime.datetime(int(liYear), liMonth, int(liDay), int(liHour), int(liMinute))

            # извлекаем название площадки проведения квиза вида "Три Лося, пр. Карла Маркса, 5, Новосибирск, Россия"
            # она хранится в 2, 5, 8 дочерних элементах
            liBar = liGamesList[i + 2].text
            # '?' в regexp нужен для non-greedy match, чтобы нашелся самый короткий матч, до первой запятой.
            # там хранится название бара ("Три Лося,...")
            liBarRegEx = re.compile(
                r'(.+?),\s.*')
            mo = liBarRegEx.search(liBar)
            liBar = mo.group(1)

            # извлекаем наличие мест на игру вида: "Есть места", "Резерв", "Нет мест"
            # информация извлекается из отдельного элемента liGamesAvailable с отдельным счетчиком k
            liAvailability = liGamesAvailable[k].text
            k += 2

            # исключаем из выборки заведомо неподходящие квизы: где нет мест, квиз уже прошел.
            # из остального формируем словарь games
            # после "Есть места" может быть пробел/перенос строки, поэтому проверяем с помощью оператора in, а не ==
            if quizDT >= curDT and 'Есть места' in liAvailability:
                games[orgTag + str(i)] = {}
                games[orgTag + str(i)]['game'] = liGameName
                games[orgTag + str(i)]['date'] = quizDT
                games[orgTag + str(i)]['bar'] = liBar
                games[orgTag + str(i)]['tag'] = liGameTag

    except Exception as err:
        # если при скрэйпиге произошла ошибка, то сохраняем ее в organizatorsErrors
        organizatorErrors[orgName] = str(err)

    return games, organizatorErrors


def scrape_mama_quiz(quizSoup, orgName, orgTag, dateParams):
    """
    Функция которая скрейпит информацию с сайта Мама Квиз и возвращает список квизов и возникших ошибок.
    :param quizSoup (bs4.BeautifulSoup): объект с HTML-кодом страницы с расписанием квизов
    :param orgName (str): имя организатора ('Мама Квиз')
    :param orgTag (str): тэг организатора ('mama')
    :param dateParams (list): список временных параметров из collect_quiz_data
    :return: games (dict), organizatorErrors (dict)
    """
    games = {}
    organizatorErrors = {}
    curYear, nextYear, curMonth, curDT = dateParams

    # так как информация о квизах на сайте Мама Квиз не упорядочена, мы создаем ряд списков и добавляем
    # на соответствующую позицию в каждый список информацию о квизе
    mamaGameNameList = []
    mamaGameTagList = []
    mamaDateList = []
    mamaStartingTimeList = []
    mamaMonthList = []
    mamaBarList = []
    endElementsIndexes = []

    try:
        # извлекаем содержимое родительского HTML-элемента, в котором хранится информация о всех квизах.
        # информация не сгруппирована по квизам, дата, название, тема и т.п. по каждому квизу является прямым
        # дочерним элементом этого элемента.
        # поэтому для Мама Квиз делаем скрейпинг эвристически:
        # сначала ищем элемент с местом проведения квиза, это ПРЕДПОЛОЖИТЕЛЬНО всегда будет последний элемент ЗНАЧИМОЙ
        # информации о квизе, позиции остальных элементов могут меняться, поэтому информация будет извлекаться
        # регулярными выражениями в интервалах от одного места проведения до другого места проведения

        # идея на будущее: искать элементы по названию стиля (style="line-height: 67px;"), но там сразу есть проблемы в
        # том что информация об игре может быть в двух разных стилях (67px и 71px)

        mamaElements = quizSoup.select('#rec487013113 > div > div > div')

        # ищем элемент с местом проведения квиза в формате 'ул. ' и записываем индексы где хранятся эти элементы
        # это почти всегда будет последний элемент со значимой информации о квизе, позиции остальных элементов еще менее
        # стабильны.
        for i, curSoupElement in enumerate(mamaElements):
            curElement = str(curSoupElement)
            tempSoup = bs4.BeautifulSoup(curElement, 'html.parser')
            try:
                result = tempSoup.find("div", {"class": "tn-atom"})
                tempText = result.text
                # информация о баре пишется в формате 'MISHKIN&MISHKIN (ул. Нарымская, 37)'
                if 'ул. ' in tempText:
                    tempIndex = tempText.index('(')
                    mamaBar = tempText[:tempIndex - 1]  # отрезаем адрес и пробел перед ним
                    mamaBarList.append(mamaBar)
                    endElementsIndexes.append(i)
                    continue

            except:
                continue

        # на основе списка индексов элементов на которые заканчивается информация о квизе формируем
        # список индексов элементов на которые начинается информация о квизе:
        # endElementsIndexes   = [20, 40, 61, 81, 101]
        # startElementsIndexes = [0, 20, 40, 61, 81]
        startElementsIndexes = endElementsIndexes.copy()
        startElementsIndexes.insert(0, 0)
        startElementsIndexes.pop(-1)

        for x, index in enumerate(startElementsIndexes):
            # ищем информацию в диапазоне между первым элементом текущего квиза startElementsIndexes[x] + 1
            # и первым элементом следующего endElementsIndexes[x]
            # startElementsIndexes[x] + 1 - чтобы повторно не смотреть элемент в котором заведомо лежит число
            # проведения квиза
            for i in range(startElementsIndexes[x] + 1, endElementsIndexes[x]):
                curElement = str(mamaElements[i])
                tempSoup = bs4.BeautifulSoup(curElement, 'html.parser')

                # пробуем извлечь значение тэга вида <div class="tn-atom" field="tn_text_1681714185448">мая</div>,
                # если его нет, то по exc продолжаем цикл
                try:
                    result = tempSoup.find("div", {"class": "tn-atom"})
                    tempText = result.text

                    # находится много пустых строк, их не обрабатываем
                    if tempText:
                        # извлекаем название игры; оно пишется капсом, решеткой и номером игры, ('ТОЛЬКО СЕРИАЛЫ #1')
                        # праздничные игры пишутся капсом и заканчиваются на год, например, 'КВИЗАНУТЫЙ НОВЫЙ ГОД 2024'
                        mamaGameNameRegEx = re.compile(r'''
                                                           ^[^а-яa-z]+        # исключаем строчные буквы
                                                           (\#\d{1,4}|        # 'решётка' и 1-4 цифры ИЛИ
                                                            2\d\d\d)$         # 2xxx год в конце названия
                                                        ''', re.VERBOSE)
                        mo = mamaGameNameRegEx.search(tempText)
                        if mo:
                            mamaGameName = mo.group()
                            # по названию игры добаляем тэг с тематикой
                            mamaGameTag = assign_themes_to_quiz(mamaGameName, orgName)
                            mamaGameNameList.append(mamaGameName)
                            mamaGameTagList.append(mamaGameTag)
                            continue  # для этого тэга не делаем других проверок

                        # извлекаем время начала игры в формате '18:00'
                        mamaStartingTimeRegEx = re.compile(r'^\d\d:\d\d$')
                        mo = mamaStartingTimeRegEx.search(tempText)
                        if mo:
                            mamaStartingTime = mo.group()
                            mamaStartingTimeList.append(mamaStartingTime)
                            continue

                        # извлекаем адрес бара по вхождению слова 'ул.', например, 'MISHKIN&MISHKIN (ул. Нарымская, 37)'
                        if 'ул. ' in tempText:
                            tempIndex = tempText.index('(')
                            mamaBar = tempText[:tempIndex - 1]  # отрезаем адрес и пробел перед ним
                            mamaBarList.append(mamaBar)
                            continue

                        # извлекаем месяц в формате 'мая'
                        if tempText in MONTH_DICT:
                            # преобразуем текстовое название месяца в цифру с помощью словаря MONTH_DICT
                            mamaMonth = MONTH_DICT[tempText]
                            mamaMonthList.append(mamaMonth)
                            continue

                        # извлекаем число проведения игры
                        mamaDateRegEx = re.compile(r'^\d{1,2}$')
                        mo = mamaDateRegEx.search(tempText)
                        if mo:
                            mamaDate = mo.group()
                            mamaDateList.append(mamaDate)

                except:
                    continue

        # получив упорядоченные листы с информацией, преобразуем ее в нужный формат и добавляем в словарь games
        for q in range(len(mamaGameNameList)):
            mamaGameName = mamaGameNameList[q]
            mamaGameTag = mamaGameTagList[q]
            mamaBar = mamaBarList[q]

            # преобразовываем дату проведения квиза в нужный формат
            mamaGameStartTime = mamaStartingTimeList[q]
            mamaHour = int(mamaGameStartTime[:2])
            mamaMinute = int(mamaGameStartTime[3:])
            mamaDay = int(mamaDateList[q])
            mamaMonth = int(mamaMonthList[q])

            # если сейчас декабрь, а расписание содержит январские квизы, то для них указываем в дате следующий год
            if curMonth == 12 and mamaMonth == 1:
                quizDT = datetime.datetime(nextYear, mamaMonth, mamaDay, mamaHour, mamaMinute)
            else:
                quizDT = datetime.datetime(curYear, mamaMonth, mamaDay, mamaHour, mamaMinute)

            # исключаем из выборки заведомо неподходящие квизы: квиз уже прошел
            # из остального формируем словарь games
            if quizDT >= curDT:
                games[orgTag + str(q)] = {}
                games[orgTag + str(q)]['game'] = mamaGameName
                games[orgTag + str(q)]['date'] = quizDT
                games[orgTag + str(q)]['bar'] = mamaBar
                games[orgTag + str(q)]['tag'] = mamaGameTag

    except Exception as err:
        # если при скрэйпиге произошла ошибка, то сохраняем ее в organizatorsErrors
        organizatorErrors[orgName] = str(err)

    return games, organizatorErrors


def scrape_quiz_please(quizSoup, orgName, orgTag, dateParams):
    """
    Функция которая скрейпит информацию с сайта Квиз Плиз и возвращает список квизов и возникших ошибок.
    :param quizSoup (bs4.BeautifulSoup): объект с HTML-кодом страницы с расписанием квизов
    :param orgName (str): имя организатора ('Квиз Плиз')
    :param orgTag (str): тэг организатора ('qp')
    :param dateParams (list): список временных параметров из collect_quiz_data
    :return: games (dict), organizatorErrors (dict)
    """
    games = {}
    organizatorErrors = {}
    curYear, nextYear, curMonth, curDT = dateParams

    try:
        # извлекаем содержимое родительского HTML-элемента, в котором хранится информация о всех квизах
        qpElements = quizSoup.select('#w1 > .schedule-column')

        # элементы массива qpElements выглядят как {'class': ['schedule-column'], 'id': '40558'}
        # по очереди извлекаем данные id, сохраняем их как selectorBeginning и извлекаем из них информацию о каждом квизе
        for i, curElement in enumerate(qpElements):
            '''Id квизов в HTML-коде хранятся в виде '40558', но в CSS-селекторах id выглядят как '#\34 0558'
            Число 34 примерно раз в полгода увеличивается на единицу, поэтому сделан цикл по подбору нужного числа:
            если тестовый элемент извлечен и над ним можно провести реально необходимую операцию, значит подобран нужный
            селектор и цикл прерывается. Если выполнение операции вылетело в Exception, то selectorNum инкрементируется.
            Необходимо чтобы цикл начинался минимум с 36, потому что такое число используется в локальных файлах
            используемых при unit-тестировании.
            Само id '0558' хранится в curElement.attrs['id'][1:]/
            '''
            for selectorNum in range(36, 100):
                try:
                    selectorBeginning = rf'#\{selectorNum} ' + curElement.attrs['id'][1:]
                    testElem = quizSoup.select(rf'{selectorBeginning} > div > div.h3.h3')
                    testElem = testElem[0].get_text(strip=True)
                    break

                except Exception:
                    # этот Exception не добавляется в organizatorsErrors, так как нужен только для подбора селектора
                    # если финальная цифра цикла все равно не подойдет, то Exception произойдет далее в коде функции
                    selectorNum += 1
                    continue

            # формируем корректный id квиза, который будет являться префиксом для CSS-селекторов нужных элементов
            selectorBeginning = rf'#\{selectorNum} ' + curElement.attrs['id'][1:]

            # извлекаем дату проведения квиза вида "12 июня, Воскресенье"
            qpDateTime = quizSoup.select(f'{selectorBeginning} > div > div.h3.h3')
            qpDateTime = qpDateTime[0].get_text(strip=True)

            # извлекаем название игры
            qpGameNameAndNum = quizSoup.select(f'{selectorBeginning} > div > div.schedule-block-top > a > div.h2.h2')
            qpGameName = qpGameNameAndNum[0].get_text(strip=True)
            qpGameNumber = qpGameNameAndNum[1].get_text(strip=True)

            # по названию игры добаляем тэг с тематикой
            qpGameTag = assign_themes_to_quiz(qpGameName, orgName)

            # извлекаем название площадки проведения квиза
            qpBar = quizSoup.select(f'{selectorBeginning} > div > div.schedule-block-top > div.schedule-info-block > '
                                    f'div:nth-child(1) > div > div:nth-child(1) > div')
            # информация о баре 'Максимилианс' может храниться в другом элементе (div:nth-child(2)
            if len(qpBar) == 0:
                qpBar = quizSoup.select(f'{selectorBeginning} > div > div.schedule-block-top > div.schedule-info-block > '
                                        f'div:nth-child(2) > div > div:nth-child(1) > div')
            qpBar = qpBar[0].get_text(strip=True)

            # извлекаем время начала квиза вида "в 20:00"
            qpStartTime = quizSoup.select(
                f'{selectorBeginning} > div > div.schedule-block-top > div.schedule-info-block > div:nth-child(2) > div > div')
            qpStartTime = qpStartTime[0].get_text(strip=True)
            # у бара 'Максимилианс' время хранится другом элементе (div:nth-child(3))
            if qpStartTime == 'Максимилианс':
                qpStartTime = quizSoup.select(f'{selectorBeginning} > div > div.schedule-block-top > div.schedule-info-block > '
                                              f'div:nth-child(3) > div > div')
                qpStartTime = qpStartTime[0].get_text(strip=True)
            # у Квиз Плиз время начали игры пишется в формате "в 20:00", поэтому 2 первых символа отрезаем
            qpStartTime = qpStartTime[2:]
            qpHour = int(qpStartTime[:2])
            qpMinute = int(qpStartTime[3:])

            # извлекаем наличие мест на игру вида: "Нет мест! Но можно записаться в резерв"/ "Осталось мало мест"
            qpPlacesLeft = quizSoup.select(f'{selectorBeginning} > div > div.schedule-block-bottom > '
                                           f'div.game-status.schedule-available.w-clearfix > div')
            if len(qpPlacesLeft) > 0:
                qpPlacesLeft = qpPlacesLeft[0].get_text(strip=True)

            # извлекаем информацию о необходимости приглашения на игру
            needInvite = quizSoup.select(f'{selectorBeginning} > div > div.schedule-block-bottom.w-clearfix > '
                                         f'div.game-status.schedule-end.w-clearfix > div')
            if len(needInvite) > 0:
                needInvite = needInvite[0].get_text(strip=True)

            # преобразовываем дату проведения квиза в нужный формат
            # regexp для даты в формате '12 июня, Воскресенье'
            qpDateRegEx = re.compile(r'''
                                    ^(\d|\d\d)\s    # одна или две цифры в начале строки, после пробел
                                    ([А-Яа-я]+),\s  # месяц, после него запятая пробел
                                    ([А-Яа-я]+)$    # день недели
                                    ''', re.VERBOSE)
            mo = qpDateRegEx.search(qpDateTime)
            qpDay, qpMonth, qpDOW = mo.groups()

            # преобразуем текстовое название месяца в цифру с помощью словаря MONTH_DICT
            qpMonth = MONTH_DICT[qpMonth]

            # если сейчас декабрь, а расписание содержит январские квизы, то для них указываем в дате следующий год
            if curMonth == 12 and qpMonth == 1:
                quizDT = datetime.datetime(nextYear, qpMonth, int(qpDay), qpHour, qpMinute)
            else:
                quizDT = datetime.datetime(curYear, qpMonth, int(qpDay), qpHour, qpMinute)

            # исключаем из выборки заведомо неподходящие квизы: где нет мест, по инвайтам, квиз уже прошел
            # из остального формируем словарь games
            if len(needInvite) == 0 and quizDT >= curDT and qpPlacesLeft != 'Нет мест! Но можно записаться в резерв':
                games[orgTag + str(i)] = {}
                games[orgTag + str(i)]['game'] = qpGameName + ' ' + qpGameNumber
                games[orgTag + str(i)]['date'] = quizDT
                games[orgTag + str(i)]['bar'] = qpBar
                games[orgTag + str(i)]['tag'] = qpGameTag

    except Exception as err:
        # если при скрэйпиге произошла ошибка, то сохраняем ее в organizatorsErrors
        organizatorErrors[orgName] = str(err)

    return games, organizatorErrors


def scrape_wow_quiz(quizSoup, orgName, orgTag, dateParams):
    """
    Функция которая скрейпит информацию с сайта WOW Quiz и возвращает список квизов и возникших ошибок.
    :param quizSoup (bs4.BeautifulSoup): объект с HTML-кодом страницы с расписанием квизов
    :param orgName (str): имя организатора ('WOW Quiz')
    :param orgTag (str): тэг организатора ('wow')
    :param dateParams (list): список временных параметров из collect_quiz_data
    :return: games (dict), organizatorErrors (dict)
    """
    games = {}
    organizatorErrors = {}
    curYear, nextYear, curMonth, curDT = dateParams

    try:
        # извлекаем содержимое родительского HTML-элемента, в котором хранится информация о всех квизах
        wowGamesList = quizSoup.select('body > div.wrapper > div.schelude-tabs > div.schelude-tabs-body > div > div > '
                                      'div > div > div > div.game-row > div')
        for n in range(1, (len(wowGamesList) + 1)):
            # формируем корректный id квиза, который будет являться префиксом для CSS-селекторов нужных элементов
            selectorBeginning = f'body > div.wrapper > div.schelude-tabs > div.schelude-tabs-body > div > div > div > '\
                                f'div > div > div.game-row > div:nth-child({n})'

            # извлекаем название игры в формате "Угадай мультфильм #4"
            wowGameName = quizSoup.select(f'{selectorBeginning} > div > div.game-item-content > '
                                         f'div.game-item-content-left > div.game-item-top > div.game-item__title')
            wowGameName = wowGameName[0].text

            # по названию игры добаляем тэг с тематикой игры
            wowGameTag = assign_themes_to_quiz(wowGameName, orgName)

            # извлекаем дату проведения квиза в формате "4 июня"
            wowGameDate = quizSoup.select(f'{selectorBeginning} > div > div.game-item-content > '
                                          f'div.game-item-content-right > div.game-item__date > span:nth-child(1)')
            wowGameDate = wowGameDate[0].text

            # извлекаем день недели в формате "суббота"
            wowGameDOW = quizSoup.select(f'{selectorBeginning} > div > div.game-item-content > '
                                         f'div.game-item-content-right > div.game-item__date > span:nth-child(2)')
            wowGameDOW = wowGameDOW[0].text

            # извлекаем время начала квиза в формате "16:00"
            wowGameStartTime = quizSoup.select(f'{selectorBeginning} > div > div.game-item-content > '
                                               f'div.game-item-content-right > div.game-item__date > span.time')
            wowGameStartTime = wowGameStartTime[0].text

            # извлекаем название площадки проведения квиза в формате "Три Лося"
            wowBar = quizSoup.select(f'{selectorBeginning} > div > div.game-item-content > '
                                     f'div.game-item-content-right > div.game-item__address > span.place')
            wowBar = wowBar[0].text

            # извлекаем наличие мест на игру вида "Места есть"/ "Резерв"
            wowAvailability = quizSoup.select(f'{selectorBeginning} > div > div.game-item-content > '
                                              f'div.game-item-content-right > span')
            wowAvailability = wowAvailability[0].text

            # преобразовываем дату проведения квиза в нужный формат
            wowHour = int(wowGameStartTime[:2])
            wowMinute = int(wowGameStartTime[3:])
            wowDateRegEx = re.compile(r'''
                                    ^(\d|\d\d)\s        # одна или две цифры в начале строки, после пробел
                                     ([А-Яа-я]+)        # месяц
                                    ''', re.VERBOSE)
            mo = wowDateRegEx.search(wowGameDate)
            wowDay, wowMonth = mo.groups()
            wowDay = int(wowDay)
            # преобразуем текстовое название месяца в цифру с помощью словаря MONTH_DICT
            wowMonth = MONTH_DICT[wowMonth]

            # если сейчас декабрь, а расписание содержит январские квизы, то для них указываем в дате следующий год
            if curMonth == 12 and wowMonth == 1:
                quizDT = datetime.datetime(nextYear, wowMonth, wowDay, wowHour, wowMinute)
            else:
                quizDT = datetime.datetime(curYear, wowMonth, wowDay, wowHour, wowMinute)

            # исключаем из выборки заведомо неподходящие квизы: нет мест, квиз уже прошел
            # из остального формируем словарь games
            if wowAvailability != 'Резерв' and quizDT >= curDT:
                games[orgTag + str(n)] = {}
                games[orgTag + str(n)]['game'] = wowGameName
                games[orgTag + str(n)]['date'] = quizDT
                games[orgTag + str(n)]['bar'] = wowBar
                games[orgTag + str(n)]['tag'] = wowGameTag

    except Exception as err:
        # если при скрэйпиге произошла ошибка, то сохраняем ее в organizatorsErrors
        organizatorErrors[orgName] = str(err)

    return games, organizatorErrors


def collect_quiz_data(cityOrganizators, cityLinks, localHTMLs=None):
    """
    Формирует перечень квизов для конкретного города.
    Собирает информацию с сайтов всех организаторов, которые указаны для данного города в config.CITY_DICT.
    Игры по приглашениям и игры у которых есть запись только в резерв исключаются из выборки.
    :param cityOrganizators (list): список организаторов, которые проводят квизы в этом городе
    :param cityLinks (list): список ссылок на разделы сайтов, где хранится информация о квизах для этого города
    :param localHTMLs (dict): для unit-тестов, словарь в котором хранятся объекты requests.get с локальных копий
                              web-страниц. См. функцию tests/conftest.py/quiz_from_local_files()
    :return games (dict): перечень квизов
    :return organizatorErrors (dict): перечень ошибок по организаторам, скрейпинг с сайтов которых не удался
    """
    global ORGANIZATORS_DICT

    games = {}
    organizatorErrors = {}

    curYear = datetime.date.today().year
    nextYear = curYear + 1
    curMonth = datetime.date.today().month
    curDT = datetime.datetime.now()
    dateParams = [curYear, nextYear, curMonth, curDT]

    # нельзя использовать mutable объекты в качестве дефолтных значений параметров функции
    # так как нам нужен localHTMLs типа dict, то переопределяем его
    if localHTMLs is None:
        localHTMLs = {}

    # проверяем есть ли 'всероссийский' организатор в данном городе, если есть извлекаем информацию о его квизах
    for orgName in ORGANIZATORS_DICT:
        if orgName in cityOrganizators:
            orgTag = ORGANIZATORS_DICT[orgName][0]
            orgLink = cityLinks[cityOrganizators.index(orgName)]
            try:
                quizSoup = get_data_from_web_page(orgName, orgLink, localHTMLs)

                if orgName == 'Квиз Плиз':
                    gamesQP, orgErrorsQP = scrape_quiz_please(quizSoup, orgName, orgTag, dateParams)
                    games = {**games, **gamesQP}  # добавляем к словарю games полученные значения из словаря **gamesQP
                    organizatorErrors = {**organizatorErrors, **orgErrorsQP}

                elif orgName == 'Лига Индиго':
                    # при скрейпинге локальной копии веб-страницы у Лиги Индиго отличается CSS-селектор.
                    # чтобы выбрать корректный селектор, передаем на вход функции доп. аргумент localHTMLs
                    gamesLI, orgErrorsLI = scrape_liga_indigo(quizSoup, orgName, orgTag, dateParams, localHTMLs)
                    games = {**games, **gamesLI}
                    organizatorErrors = {**organizatorErrors, **orgErrorsLI}

                elif orgName == 'Мама Квиз':
                    gamesMama, orgErrorsMama = scrape_mama_quiz(quizSoup, orgName, orgTag, dateParams)
                    games = {**games, **gamesMama}
                    organizatorErrors = {**organizatorErrors, **orgErrorsMama}

                elif orgName == 'WOW Quiz':
                    gamesWow, orgErrorsWow = scrape_wow_quiz(quizSoup, orgName, orgTag, dateParams)
                    games = {**games, **gamesWow}
                    organizatorErrors = {**organizatorErrors, **orgErrorsWow}

            except Exception as err:
                organizatorErrors[orgName] = str(err)

    return games, organizatorErrors


def create_formatted_quiz_list(games, organizatorErrors, **kwargs):
    """
    Упорядочивает квизы разных организаторов по дате проведения игры.
    Исключает из общего списка квизы не подходящие под предпочтения пользователя.
    Преобразует информацию в необходимый для вывода telegram-бота формат:
    1. <b>Лига Индиго</b>: Игра №1 Сезон №11. Бар: Три Лося, понедельник, 15 января, 19:30\n'

    :param games (dict): перечень квизов, формируется в collect_quiz_data()
    :param organizatorErrors (dict): перечень ошибок по организаторам, скрейпинг с сайтов которых не удался
    :param kwargs:
        dow (list): дни проведения квиза (будни/ выходные/ любой); выбираются в ходе чата
        selected_theme (str): тематика проведения квиза (Классика/ Мультимедиа / т.п.); выбирается в ходе чата
        excl_bar (str): бары, которые нужно перманентно исключать из выборки; берется из пользовательских /preferences
        excl_theme (str): тематики, которые нужно перманентно исключать; берется из пользовательских /preferences.
        excl_orgs (str): организаторы, которых нужно перманентно исключать; берется из пользовательских /preferences
    :return quizList (list): итоговый список квизов для отображения в telegram-боте
    """

    dateList = []
    indexList = []
    quizList = []

    # извлекаем все нужные для работы функции keyword arguments из **kwargs
    dow = kwargs.get('dow')
    selected_theme = kwargs.get('selected_theme')
    excl_bar = kwargs.get('excl_bar')
    excl_theme = kwargs.get('excl_theme')
    excl_orgs = kwargs.get('excl_orgs')
    # если одного из обязательных аргументов нет, то выводим в лог сообщения об ошибке и возвращаем пустой список
    if dow is None or selected_theme is None or excl_bar is None or excl_theme is None or excl_orgs is None:
        logger.error(f'На вход функции create_formatted_quiz_list не были переданы все необходимые kwargs:'
                     f'{kwargs}')
        return quizList

    # формируем словарь соответствия тэга организатора (содержится в элементах games) названию организатора,
    # чтобы можно было извлекать название организатора по индексу:
    # {'qp': 'Квиз Плиз', 'li': 'Лига Индиго', 'mama': 'Мама Квиз', 'wow': 'WOW Quiz'},
    organizatorIndexMapping = {}
    for curOrgName in ORGANIZATORS_DICT:
        curOrgIndex = ORGANIZATORS_DICT[curOrgName][0]
        organizatorIndexMapping[curOrgIndex] = curOrgName

    # формируем 2 списка для их последующей синхронной сортировки:
    # indexList - индексы квиза вида li1, wow24, qp6, по которым далее будем извлекать информацию из games
    # dateList - даты проведения квиза, по которым далее будем сортировать оба списка
    for quizIndex in games:
        indexList.append(quizIndex)
        curGameParams = games.get(quizIndex)
        curGameDate = curGameParams.get('date')
        dateList.append(curGameDate)

    # распологаем элементы списка индексов в том же порядке, в котором расположены элементы списка дат после
    # сортировки по возрастанию
    indexList = [indexList for _,indexList in sorted(zip(dateList, indexList))]

    # извлекем из словаря games информацию в отсортированном порядке
    k = 0 # порядковый номер квизов, попавших в итоговый вывод функции
    for i in indexList:
        # из индекса i вида li3, regexp-ом извлекаем тэг организатора вида 'li'
        # по тэгу извлекаем название организатора вида 'Лига Индиго'
        # если этот организатор исключен пользователем из выборки в /preferences, то переходим к следующему шагу цикла
        orgIndexRegex = re.compile(r'^([a-zA-Z]+)(\d{1,})$')
        mo = orgIndexRegex.search(i)
        curOrgTag = mo[1]
        curOrgName = organizatorIndexMapping[curOrgTag]
        if curOrgName in excl_orgs:
            continue
        else:
            # делаем форматирование, чтобы название организатора выводилось жирным шрифтом. '<b>Лига Индиго</b>'
            organizator = '<b>' + curOrgName + '</b>'

        # исключаем из выборки места проведения квизов, перманентно исключенные пользователем из выборки в /preferences
        if games[i]['bar'].lower() in excl_bar.lower():
            continue

        # оставляем только ту тематику, которую пользователь выбрал в ходе чата
        # если пользователь выбрал вариант 'Оставить все' (QUIZ_THEMES[0]), то ничего не исключается
        if selected_theme != QUIZ_THEMES[0] and selected_theme not in games[i]['tag']:
            continue

        # исключаем тематики, перманентно исключенные пользователем из выборки в /preferences.
        # например, у игры 'Музыка СССР' есть тематики 'Мультимедиа' и 'Ностальгия'
        # пользователь в чате выбрал 'Мультимедиа', а в исключениях у него 'Ностальгия'. такую игру исключаем.
        # если пользователь в чате выбрал 'Оставить все', то игры с тематиками из /preferences все равно будут исключены
        else:
            # чтобы завершить внутренний цикл for t in games[i]['tag'] после первого же найденного совпадающего тэга
            # и перейти к следующему шагу внешнего цикла for i in indexList используется переменная mainLoopState
            mainLoopState = False
            for t in games[i]['tag']:
                if t in excl_theme:
                    mainLoopState = True
                    break  # прерываем inner loop
            if mainLoopState:
                continue  # прерываем outer loop

        # извлекаем информацию о дате проведения квиза
        quizDate = games[i]['date']
        quizTime = quizDate.time()

        # преобразуем время в читаемый формат HH:MM
        quizTime = quizTime.isoformat('minutes')

        # исключаем дни недели не подходящие под выбранное пользователем значение dow
        # например, если пользователь выбрал Выходные (dow = [6,7]), то исключаем все квизы проходящие в будние дни
        quizDOW = quizDate.isoweekday()
        if quizDOW in dow:
            # после того как квиз прошел все возможные фильтрации и принято решение о его попадании в итоговую выборку
            # ему присваивается уникальный порядковый номер, который будет виден в выводе telegram-бота
            # по этому номеру можно будет создать голосование хочет ли ваша команда пойти на данную игру
            k += 1

            # получаем из словаря MONTH_DICT название месяца (key) по порядковому номеру месяца (value)
            # https://stackoverflow.com/questions/8023306/get-key-by-value-in-dictionary
            quizMonth = list(MONTH_DICT.keys())[list(MONTH_DICT.values()).index(quizDate.month)]

            # извлекаем из словаря DOW_DICT название дня недели по его порядковому номеру (1 - Понедельник)
            quizDOWReadable = DOW_DICT[quizDOW]

            # приводим дату к читаемому виду "26 июня, 18:00"
            quizDateReadable = str(quizDate.day) + ' ' + quizMonth + ', ' + quizTime

            # делаем итоговое форматирование строки о квизе вида:
            # 1. <b>Лига Индиго</b>: Игра №1 Сезон №11. Бар: Три Лося, понедельник, 15 января, 19:30\n'
            quizReadable = f"{k}. {organizator}: {games[i]['game']}. Бар: {games[i]['bar']}, {quizDOWReadable}, " \
                           f"{quizDateReadable}\n"
            quizList.append(quizReadable)

    # если при запросе информации по каким-то организаторам были ошибки - выводим пользователю это сообщение
    if len(organizatorErrors) > 0:
        quizList.append('\nК сожалению не удалось получить информацию по следующим организаторам: ')
        for e in organizatorErrors:
            quizList.append(e)
        quizList.append('\nПопробуй запросить информацию по ним позже.')

    return quizList







