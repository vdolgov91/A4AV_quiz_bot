#! python3
# quizAggregator.py - aggregate & filter data about quiz games in Novosibirsk

#TODO LIST:

#когда 2023-02-22 делал запрос /all вернулось
#File "D:\Python\_dolgov\A4AV_bot\venv\lib\site-packages\telegram\request\_baserequest.py", line 328, in _request_wrapper
#    raise BadRequest(message)
#+telegram.error.BadRequest: Message is too long

#сделать сценарии тестирования
#сделать рефактор с учетом всех замечаний из beyond the basic stuff
#исключить config.py из копирования в git-репозиторий, задать системные параметры через переменные среды
#добавить Мозгобойню, Эйнштейн Пати, Угадай мелодию, Сибквиз, QuizClub, других оргов?
#добавить получение ссылки на регистрацию
#добавить функцию которая будет формировать список баров для нового города
#посмотреть можно ли как-то поправить проблему с квиз плизовским селектором #\34 0558


#для докера:
#для контейнеризации создать папку с базой данных (app_db создана) и папку с логами, поменять адрес в конфиге. При запуске контейнера мапить в нужный volume
#передавать переменные окружения можно ввиде docker run ... -e MYSQL_ROOT_PASSWORD=secret
#хотя это не рекомендуется https://blog.diogomonica.com//2017/03/27/why-you-shouldnt-use-env-variables-for-secret-data/
#проработать проверку health, чтобы если бот сломался по неопределенной причине контейнер перезапустился

#если в группе запускаешь preferences, то нет возможности прервать опрос, не доступен список команд (в отличии от общения в личке). можно или добавить кастомных кнопок Прервать опрос или как-то команду /bye в текст ввернуть


#изучаем страницу с помощью dev tools, в хроме это f12
#наводим на нужный элемент ПКМ и "Просмотреть код" - смотрим какой элемент отвечает за нужную часть страницы
#жмем в html-коде на нужный элемент ПКМ и Copy - Copy selector, по этому css-селектору можно обращаться к элементу
#у bs4 есть траблы при поиске селектора по цифровому id, в таком случае используем стринговый тэг r'

import requests, bs4, datetime, re
from config import (
    logger,
    cityDict,
    organizatorsDict,
    themeMappingDict,
    themes
)

#заводим словарь соответствия названия месяцев в родительном падеже порядковому номеру месяца в integer
MonthDict = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
dowDict = {1: 'понедельник', 2: 'вторник', 3: 'среда', 4: 'четверг', 5: 'пятница', 6: 'суббота', 7: 'воскресенье'}
#dowDictReverse = {'понедельник': 1, 'вторник': 2, 'среда': 3, 'четверг': 4, 'пятница': 5, 'суббота': 6, 'воскресенье': 7}
qpName = ''
liName = ''
wowName = ''

# функция которая формирует набор информации индивидуальной для города проведения - организаторы, ссылки на их сайты, бары
# пока информация создана только для Новосибирска, это задел на будущее, чтобы бот можно было дорабатывать
def createInfoByCity(city):
    # этот элемент списка необходим для формирования опроса по исключению организаторов
    cityOrganizators = ['Оставить всех организаторов']
    # добавляем placeholder на 0 позицию cityLinks, так как у cityOrganizators есть нулевой элемент "Оставить всех организаторов"
    # таким образом название организатора и ссылка на его сайт будут находиться на одной позиции
    cityLinks = ['placeholder']

    # проверяем есть ли такой город в слове cityDict. Если нет, то возвращаем три пустых list-а
    if city not in cityDict:
        logger.info('Информации по квизам, проводимым в городе %s пока нет.', city)
        return [], [], []

    # формируем список баров в городе для создания опроса в формате
    # ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки вверх']
    cityBars = ['Оставить все бары'] + cityDict[city]['bars']

    # формируем ссылки на сайты всех организаторов, присутствующих в городе
    # первое условие: проверяем есть ли такой ключ в словаре, второе условие: не является ли значение ключа пустым
    # если организатор присутствует в городе - формируем ссылку и добавляем его в список организаторов

    for curOrg in organizatorsDict:
        #словарь organizatorsDict организован в виде {'Лига Индиго': ['li','https://ligaindigo.ru/<city_tag>']}, соответственно
        #curOrg=Лига Индиго, curTag='li', curBaseUrl='https://ligaindigo.ru/<city_tag>'
        curTag = organizatorsDict[curOrg][0]
        curBaseUrl = organizatorsDict[curOrg][1]
        if cityDict[city].get(curTag) != None and cityDict[city][curTag]:
            curCityTag = cityDict[city][curTag]
            curLink = curBaseUrl.replace('<city_tag>', curCityTag) #заменяем плэйсхолдер на тэг конкретного города
            cityLinks.append(curLink) #добавляем итоговую ссылку в лист
            cityOrganizators.append(curOrg) #добавляем название организатора в лист
        #elif curOrg == 'Мама Квиз' and cityDict[city].get(curTag) != None and not cityDict[city][curTag]:
        # специальное условие для Мама Квиз в Новосибирске, так как у него НЕ БЫЛО отдельного тэга для города
        # в таком случае тэг есть, а значение пустое: 'mama_city_tag': ''
        # https://mamaquiz.ru/
            #curCityTag = cityDict[city][curTag]
            #curLink = curBaseUrl.replace('<city_tag>.', '') #удаляем из ссылки <...>., чтобы привести ее к нужному виду
            #cityLinks.append(curLink)
            #cityOrganizators.append(curOrg)

    # добавляем к списку всероссийских организаторов местных организаторов, идут по алфавиту после всех всероссийских
    # на настоящий момент функционал не используется, заготовка на будущее
    localOrgs = cityDict[city].get('local_organizators')
    if localOrgs:
        for curDict in localOrgs:
            link = curDict.get('link')
            name = curDict.get('name')
            # добавляем информацию по местным организаторам только если оба значения извлеклись корректно
            if link and name:
                cityLinks.append(link)
                cityOrganizators.append(name)
            else:
                logger.error(
                    'Не получилось извлечь название или ссылку на сайт местного организатора по городу %s, вероятно ошибка в словаре в этой строке: %s',
                    city, curDict)
    logger.debug('По городу %s сформированы списки баров: %s, организаторов: %s, ссылок на сайты организаторов: %s',
                 city, str(cityBars), str(cityOrganizators), str(cityLinks))
    return cityBars, cityOrganizators, cityLinks

def assignThemesToQuiz(gamename, organizator):
    gamename = gamename.lower()
    # print('organizator: %s, gamename: %s' %(organizator, gamename))
    tags = []
    if organizator == 'Лига Индиго':
        # доп проверка для игр с названием вида 'Игра №2 Сезон №7'
        # liGameNameRegEx = re.compile(r'^(\d+)\s+игр.*(\d+)\s+сезон.*') - такой формат был раньше '10 игра 14 сезона'
        liGameNameRegEx = re.compile(r'^[Ии]гра\s+№(\d+)\s+[Сс]езон.*')  # формат 2023 - 'Игра №2 Сезон №7'
        mo = liGameNameRegEx.search(gamename)
        if mo != None:
            tags.append('Классика')


    # k = тематика('Классика'), themeMappingDict[k] = словарь тематики(['18+', 'чёрный квиз']), j = тэг из словаря('чёрный квиз')
    for k in themeMappingDict: #по очереди перебираем все тематики
         for j in themeMappingDict[k]: #перебираем все тэги внутри тематики
             if j in gamename: #если нашлось вхождение тэга в название игры, то добавляем этот тэг в список
                tags.append(k)
                break
    #print('для ' + gamename + ' присвоены tags: ' + str(tags))
    return tags

# функция которая опрашивает сайты организаторов и формирует полный список игр
# на текущий момент она исключает игры по приглашениям и игры у которых есть запись только в резерв/нет мест
def collectQuizData(cityOrganizators, cityLinks, localHTMLs=[]):
    ########################################### Квиз, плиз!
    curYear = datetime.date.today().year
    nextYear = curYear + 1
    curMonth = datetime.date.today().month
    curDT = datetime.datetime.now()
    games = {}  # в этот словарь запишем все игры, подходящие под наши условия
    organizatorErrors = {}  # в этот словарь запишем сайты организаторов по которым не удалось получить информацию из-за каких либо ошибок и возникшую ошибку

    qpName = 'Квиз Плиз'
    if qpName in cityOrganizators:
        try:
            orgTag = organizatorsDict[qpName][0]  # тэг организатора, например qp
            qpLink = cityLinks[cityOrganizators.index(qpName)] # ссылка находится на том же элементе массива, что и название организатора
            #print('qpLink: ' + qpLink)
            if len(localHTMLs) == 0:
                quizPlease = requests.get(qpLink)
                #выбрасываем ошибку если страница Квиз Плиз недоступа
                quizPlease.raise_for_status()
            else:
                quizPlease = localHTMLs[qpName]
            #мы отправляем в bs4 именно quizPlease.text, так как Html именно там
            qpSoup = bs4.BeautifulSoup(quizPlease.text, 'html.parser')
            #в элементе <div_id="w1" ....>, в классах schedule-column хранятся все доступные игры
            #каждая игра будет отдельным элементом массива qpElemets
            qpElements = qpSoup.select('#w1 > .schedule-column')

            #элементы массива выглядят как {'class': ['schedule-column'], 'id': '40558'}
            #мы по очереди извлекаем id, записываем их как curQuizId, далее извлекаем элементы каждого квиза
            for i in range(len(qpElements)):
                '''Id квизов в html-коде хранятся в виде '40558', но в css-селекторах id выглядят как '#\34 0558'
                Число 34 примерно раз в полгода увеличивается на единицу, поэтому сделан цикл по подбору нужного числа:
                если тестовый элемент извлечен и над ним можно провести реально необходимую операцию, то селектор нужный
                и цикл прерывается (break). Если выполнение операции вылетело в Exception, то цифра инкриментируется.
                Необходимо чтобы цикл начинался минимум с 36, потому что такое число используется в локальных файлах
                используемых при тестировании.
                Само id '0558' хранится в qpElements[i].attrs['id'][1:]/
                '''
                for selectorNum in range(36, 100):
                    try:
                        curQuizId = rf'#\{selectorNum} ' + qpElements[i].attrs['id'][1:]
                        testElem = qpSoup.select(rf'{curQuizId} > div > div.h3.h3')
                        testElem = testElem[0].get_text(strip=True)
                        break

                    except Exception:
                        selectorNum += 1
                        continue


                curQuizId = rf'#\{selectorNum} ' + qpElements[i].attrs['id'][1:]
                #вытаскиваем дату проведения вида "12 июня, Воскресенье"
                #у h3.h3 есть разные цвета, green - игра для всех, pink - игра по инвайтам
                qpDateTime = qpSoup.select(rf'{curQuizId} > div > div.h3.h3')
                qpDateTime = qpDateTime[0].get_text(strip=True)

                #вытаскиваем название игры
                qpGameNameAndNum = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-top > a > div.h2.h2')
                qpGameName = qpGameNameAndNum[0].get_text(strip=True)
                qpGameNumber = qpGameNameAndNum[1].get_text(strip=True)

                #по названию игры добаляем тэг с тематикой
                qpGameTag = assignThemesToQuiz(qpGameName, qpName)

                #вытаскиваем площадку, для Максимилианса отдельное правило
                qpBar = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-top > div.schedule-info-block > div:nth-child(1) > div > div:nth-child(1) > div')
                if len(qpBar) == 0:
                    qpBar = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-top > div.schedule-info-block > div:nth-child(2) > div > div:nth-child(1) > div')
                qpBar = qpBar[0].get_text(strip=True)

                #вытаскиваем время начала вида "в 20:00"
                qpStartTime = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-top > div.schedule-info-block > div:nth-child(2) > div > div')
                #select вернет всю строку с тэгом, get_text вернет только значение, strip=True отрежет лишние отступы и пробелы
                qpStartTime = qpStartTime[0].get_text(strip=True)
                #у Максимилианса время почему-то хранится в div:nth-child(3)
                if qpStartTime == 'Максимилианс':
                    qpStartTime = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-top > div.schedule-info-block > div:nth-child(3) > div > div')
                    qpStartTime = qpStartTime[0].get_text(strip=True)
                #у Квиз Плиз время написано как "в 20:00", поэтому 2 первых символа отрезаем
                qpStartTime = qpStartTime[2:]
                qpHour = int(qpStartTime[:2])
                qpMinute = int(qpStartTime[3:])

                #вытаскиваем цену вида '400₽ с человека, наличные или карта'
                qpPrice = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-top > div.schedule-info-block > div.schedule-info.last > div > div')
                qpPrice = qpPrice[0].get_text(strip=True)
                qpPrice = qpPrice[:3]

                #вытаскиваем сколько осталось мест: "Нет мест! Но можно записаться в резерв"/ "Осталось мало мест"
                qpPlacesLeft = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-bottom > div.game-status.schedule-available.w-clearfix > div')
                if len(qpPlacesLeft) > 0:
                    qpPlacesLeft = qpPlacesLeft[0].get_text(strip=True)

                #узнаем нужен ли на игру инвайт
                needInvite = qpSoup.select(rf'{curQuizId} > div > div.schedule-block-bottom.w-clearfix > div.game-status.schedule-end.w-clearfix > div')
                if len(needInvite) > 0:
                    needInvite = needInvite[0].get_text(strip=True)






                #преобразовываем дату в нужный формат
                #regexp для квиз плиза у кого дата в формате '12 июня, Воскресенье'
                qpDateRegEx = re.compile(r'''
                                        ^(\d|\d\d)\s    #одна или две цифры в начале строки, после пробел
                                        ([А-Яа-я]+),\s  #месяц, после него запятая пробел
                                        ([А-Яа-я]+)$    #день недели
                                        ''', re.VERBOSE)
                mo = qpDateRegEx.search(qpDateTime)
                qpDay, qpMonth, qpDOW = mo.groups()

                #преобразуем текстовое название месяца в цифру с помощью словаря MonthDict
                qpMonth = MonthDict[qpMonth]

                #если сейчас декабрь, а расписание на январь, то указываем следующий год
                if curMonth == 12 and qpMonth == 1:
                    quizDT = datetime.datetime(nextYear, qpMonth, int(qpDay), qpHour, qpMinute)
                else:
                    quizDT = datetime.datetime(curYear, qpMonth, int(qpDay), qpHour, qpMinute)

                #отбрасываем заведомо неподходящие квизы: где нет мест, по инвайтам, квиз уже прошел
                #из подходящих формируем словарь
                if len(needInvite) == 0 and quizDT >= curDT and qpPlacesLeft != 'Нет мест! Но можно записаться в резерв':
                    games[orgTag+str(i)]={}
                    games[orgTag+str(i)]['game'] = qpGameName + ' ' + qpGameNumber
                    games[orgTag+str(i)]['date'] = quizDT
                    games[orgTag+str(i)]['bar'] = qpBar
                    games[orgTag+str(i)]['tag'] = qpGameTag
                    #games[orgTag+str(i)]['price'] = qpPrice
        except Exception as err:
            organizatorErrors[qpName] = str(err)

    ########################################### Лига Индиго
    liName = 'Лига Индиго'
    if liName in cityOrganizators:
        try:
            orgTag = organizatorsDict[liName][0]  # тэг организатора, например qp
            liLink = cityLinks[cityOrganizators.index(liName)]  # ссылка находится на том же элементе массива, что и название организатора
            #print('liLink: ' + liLink)
            if len(localHTMLs) == 0:
                ligaIndigo = requests.get(liLink)
                ligaIndigo.raise_for_status()
            else:
                ligaIndigo = localHTMLs[liName]
            liSoup = bs4.BeautifulSoup(ligaIndigo.text, 'html.parser')
            #почему-то полный путь по css selector ничего не возвращает, поэтому далее парсим ручками
            if len(localHTMLs) == 0:
                liGamesList = liSoup.select(r'#info > div > div > div')
            else:
                # для локальной копии почему-то не работает селектор как для подключения к реальной странице
                liGamesList = liSoup.select(r'#info > div > div > div > div > div > div > div')

            logger.debug(f'liGamesList: {liGamesList}')
            #информация о наличии мест лежит в другом месте, в 0,2,4... элементах
            liGamesAvailable = liSoup.select(r'#info > div > div')

            #в 0,3,6 и т.д элементах хранятся названия квизов вида "10 игра 4 сезона"

            k = 0 #для цикла по liGamesAvailable, где нужен шаг +2
            for i in range(0,len(liGamesList),3):
                liGameName = liGamesList[i].text
                liGameTag = assignThemesToQuiz(liGameName, liName)

                #в 1,4,7 элементах лежит дата в виде "13 Июня 2022 в 19:30"
                liDateTime = liGamesList[i+1].text
                liDateRegEx = re.compile(r'''
                       ^(\d|\d\d)\s         #одна или две цифры в начале строки, после пробел
                       ([А-Яа-я]+)\s        #месяц, после него запятая пробел
                       (\d{4}).*            #год и любые символы
                       (\d\d):(\d\d)$       #часы:минуты
                       ''', re.VERBOSE)
                mo = liDateRegEx.search(liDateTime)
                liDay, liMonth, liYear, liHour, liMinute = mo.groups()
                liMonth = MonthDict[liMonth.lower()] #в словаре записано в нижнем регистре, а на сайте с заглавной
                quizDT = datetime.datetime(int(liYear), liMonth, int(liDay), int(liHour), int(liMinute))
                #в 2,5,8 элементах лежит бар в виде "Три Лося, пр. Карла Маркса, 5, Новосибирск, Россия"
                liBar = liGamesList[i+2].text
                liBarRegEx = re.compile(r'(.+?),\s.*') #? нужен для non-greedy match, чтобы нашелся самый короткий матч, до первой запятой
                mo = liBarRegEx.search(liBar)
                liBar = mo.group(1)
                #варианты: Есть места, Резерв, Нет мест
                liAvailability = liGamesAvailable[k].text
                k += 2
                # после "Есть места" может быть пробел/перенос строки, поэтому проверяем методом in
                if quizDT >= curDT and 'Есть места' in liAvailability:
                    games[orgTag+str(i)]={}
                    games[orgTag+str(i)]['game'] = liGameName
                    games[orgTag+str(i)]['date'] = quizDT
                    games[orgTag+str(i)]['bar'] = liBar
                    games[orgTag+str(i)]['tag'] = liGameTag
        except Exception as err:
            organizatorErrors[liName] = str(err)

    ########################################### WOW Quiz/ Эйнштейн Party
    wowName = 'WOW Quiz/ Эйнштейн Party'
    if wowName in cityOrganizators:
        try:
            orgTag = organizatorsDict[wowName][0]
            wowLink = cityLinks[cityOrganizators.index(wowName)]  # ссылка находится на том же элементе массива, что и название организатора
            #print('wowLink: ' + wowLink)
            if len(localHTMLs) == 0:
                wowQuiz = requests.get(wowLink)
                wowQuiz.raise_for_status()
            else:
                wowQuiz = localHTMLs[wowName]
            wowSoup = bs4.BeautifulSoup(wowQuiz.text, 'html.parser')
            #у WOW все игры лежат по селектору вида:
            #body > div.wrapper > div.schelude-tabs > div.schelude-tabs-body > div > div > div > div > div > div.game-row > div:nth-child(1)
            #поэтому сначала узнаем сколько там элементов, а потом проходимся по каждому элементу
            wowGamesList = wowSoup.select(r'body > div.wrapper > div.schelude-tabs > div.schelude-tabs-body > div > div > div > div > div > div.game-row > div')
            for n in range(1, (len(wowGamesList)+1)):
                #добавляем ключ f и используем переменную {n} в качестве указателя элмента div:nth-child(1)
                selectorBeginning = f'body > div.wrapper > div.schelude-tabs > div.schelude-tabs-body > div > div > div > div > div > div.game-row > div:nth-child({n})'
                #извлекаем имя квиза в формате "Угадай мультфильм #4"
                wowGameName = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-left > div.game-item-top > div.game-item__title')
                wowGameName = wowGameName[0].text
                # по названию игры добаляем тэг с тематикой игры
                wowGameTag = assignThemesToQuiz(wowGameName, wowName)
                #извлекаем дату проведение в формате "4 июня"
                wowGameDate = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-right > div.game-item__date > span:nth-child(1)')
                wowGameDate = wowGameDate[0].text
                #извлекаем день недели в формате "суббота"
                wowGameDOW = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-right > div.game-item__date > span:nth-child(2)')
                wowGameDOW = wowGameDOW[0].text
                #извлекаем время начала в формате "16:00"
                wowGameStartTime = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-right > div.game-item__date > span.time')
                wowGameStartTime = wowGameStartTime[0].text
                #извлекаем название бара в формате "Три Лося"
                wowBar = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-right > div.game-item__address > span.place')
                wowBar = wowBar[0].text
                #извлекаем цену в формате "400Р"
                wowPrice = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-right > div.game-item__price')
                wowPrice = wowPrice[0].text
                #извлекаем доступность в формате "Места есть"/ "Резерв"
                wowAvailability = wowSoup.select(rf'{selectorBeginning} > div > div.game-item-content > div.game-item-content-right > span')
                wowAvailability = wowAvailability[0].text

                #формируем дату квиза в формате datetime
                wowHour = int(wowGameStartTime[:2])
                wowMinute = int(wowGameStartTime[3:])
                wowDateRegEx = re.compile(r'''
                            ^(\d|\d\d)\s        #одна или две цифры в начале строки, после пробел
                             ([А-Яа-я]+)        #месяц
                            ''', re.VERBOSE)
                mo = wowDateRegEx.search(wowGameDate)
                wowDay, wowMonth = mo.groups()
                wowDay = int(wowDay)
                #преобразуем текстовое название месяца в цифру с помощью словаря MonthDict
                wowMonth = MonthDict[wowMonth]

                #если сейчас декабрь, а расписание на январь, то указываем следующий год
                if curMonth == 12 and wowMonth == 1:
                    quizDT = datetime.datetime(nextYear, wowMonth, wowDay, wowHour, wowMinute)
                else:
                    quizDT = datetime.datetime(curYear, wowMonth, wowDay, wowHour, wowMinute)

                if wowAvailability != 'Резерв' and quizDT >= curDT:
                    games[orgTag+str(n)]={}
                    games[orgTag+str(n)]['game'] = wowGameName
                    games[orgTag+str(n)]['date'] = quizDT
                    games[orgTag+str(n)]['bar'] = wowBar
                    games[orgTag+str(n)]['tag'] = wowGameTag
                    #games[orgTag+str(n)]['price'] = wowPrice
        except Exception as err:
            organizatorErrors[wowName] = str(err)

    ########################################### Мама Квиз
    mamaName = 'Мама Квиз'
    if mamaName in cityOrganizators:
        try:
            orgTag = organizatorsDict[mamaName][0]
            mamaLink = cityLinks[cityOrganizators.index(mamaName)]
            #для Мама Квиза нужно добавить header User-agent, значение можно взять из своего браузера, без него вернет 403 Forbidden
            userAgent = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'}
            if len(localHTMLs) == 0:
                mamaQuiz = requests.get(mamaLink, headers = userAgent)
                mamaQuiz.raise_for_status()
            else:
                mamaQuiz = localHTMLs[mamaName]
            mamaGameNameList = []
            mamaGameTagList = []
            mamaDateList = []
            mamaStartingTimeList = []
            mamaMonthList = []
            mamaBarList = []
            startElementsIndexes = []
            mamaSoup = bs4.BeautifulSoup(mamaQuiz.text, 'html.parser')
            # #rec487013113 > div > div - корневой элемент где хранится вся информация о квизах. информация не сгруппирована по квизам,
            # каждый элемент (дата, название, тема и т.п.) являются children-ом данного элемента.
            # сначала ищем элемент с числом проведения квиза, это почти всегда будет первый элемент информации о квизе, позиции остальных
            # элементов могут меняться, поэтому информация будет извлекаться регулярными выражениями
            mamaElements = mamaSoup.select('#rec487013113 > div > div > div')

            # ищем элемент с числом проведения квиза в формате 01-31 и записываем индексы где хранятся эти элементы
            # это почти всегда будет первый элемент информации о квизе, позиции остальных элементов еще менее стабильны
            # эта логика должна отработать корректно для всех случаев когда у первого квиза этот элемент является первым
            for i, curSoupElement in enumerate(mamaElements):
                curElement = str(curSoupElement)
                tempSoup = bs4.BeautifulSoup(curElement, 'html.parser')
                try:
                    result = tempSoup.find("div", {"class": "tn-atom"})
                    tempText = result.text
                    if tempText:
                        mamaDateRegEx = re.compile(r'^\d{1,2}$')
                        mo = mamaDateRegEx.search(tempText)
                        if mo:
                            mamaDate = mo.group()
                            mamaDateList.append(mamaDate)
                            startElementsIndexes.append(i)
                            continue

                except:
                    continue

            # на основе списка индексов элементов с которых начинается информация о квизе формируем
            # список индексов элементов на которых заканчивается информация о квизе:
            # startElementsIndexes = [9, 29, 50, 69, 93]
            # endElementsIndexes   = [29, 50, 69, 93, 111]
            endElementsIndexes = startElementsIndexes.copy()
            endElementsIndexes.pop(0)  # удаляем первый элемент, сдвигаем остальные влево
            finalElementIndex = len(mamaElements)
            endElementsIndexes.append(finalElementIndex)  # в качестве последнего индекса указываем последний элемент

            for x, index in enumerate(startElementsIndexes):
                # ищем информацию между первым элементом текущего квиза startElementsIndexes[x] + 1
                # и первым элементом следующего endElementsIndexes[x]
                # startElementsIndexes[x] + 1 - чтобы повторно не смотреть элемент в котором заведомо лежит число проведения квиза
                for i in range(startElementsIndexes[x] + 1, endElementsIndexes[x]):
                    curElement = str(mamaElements[i])
                    tempSoup = bs4.BeautifulSoup(curElement, 'html.parser')
                    # пробуем извлечь значение тэга вида <div class="tn-atom" field="tn_text_1681714185448">мая</div>, если его нет, то по exc продолжаем цикл
                    try:
                        result = tempSoup.find("div", {"class": "tn-atom"})
                        tempText = result.text
                        # находится много пустых строк, их не обрабатываем
                        if tempText:
                            # извлекаем название игры; оно пишется капсом, решеткой и номером игры, например, 'ТОЛЬКО СЕРИАЛЫ #1'
                            # праздничные игры пишутся капсом и заканчиваются на год, например, 'КВИЗАНУТЫЙ НОВЫЙ ГОД 2024'
                            mamaGameNameRegEx = re.compile(r'''
                                                                           ^[^а-яa-z]+        #исключаем строчные буквы
                                                                           (\#\d{1,4}|        #'решётка' и 1-4 цифры ИЛИ
                                                                           2\d\d\d)$          #2xxx год в конце названия
                                                                           ''', re.VERBOSE)
                            mo = mamaGameNameRegEx.search(tempText)
                            if mo:
                                mamaGameName = mo.group()
                                mamaGameTag = assignThemesToQuiz(mamaGameName, mamaName)
                                mamaGameNameList.append(mamaGameName)
                                mamaGameTagList.append(mamaGameTag)
                                continue  # для этого тэга не делаем других проверок

                            # извлекаем время начала игры, например, '18:00'
                            mamaStartingTimeRegEx = re.compile(r'^\d\d:\d\d$')
                            mo = mamaStartingTimeRegEx.search(tempText)
                            if mo:
                                mamaStartingTime = mo.group()
                                mamaStartingTimeList.append(mamaStartingTime)
                                continue

                            # извлекаем адрес бара по вхождению 'ул.', например, 'MISHKIN&MISHKIN (ул. Нарымская, 37)'
                            if 'ул. ' in tempText:
                                tempIndex = tempText.index('(')
                                mamaBar = tempText[:tempIndex - 1]  # отрезаем адрес и пробел перед ним
                                mamaBarList.append(mamaBar)
                                continue

                            # извлекаем месяц в формате 'мая'
                            if tempText in MonthDict:
                                mamaMonth = MonthDict[tempText]
                                mamaMonthList.append(mamaMonth)
                                continue

                    except:
                        continue

            # получив упорядоченные листы с информацией, преобразуем ее в нужный формат и добавим в словарь games
            for q in range(len(mamaGameNameList)):
                mamaGameName = mamaGameNameList[q]
                mamaGameTag = mamaGameTagList[q]
                mamaBar = mamaBarList[q]
                # формируем дату квиза в формате datetime
                mamaGameStartTime = mamaStartingTimeList[q]
                mamaHour = int(mamaGameStartTime[:2])
                mamaMinute = int(mamaGameStartTime[3:])
                mamaDay = int(mamaDateList[q])
                mamaMonth = int(mamaMonthList[q])
                # если сейчас декабрь, а расписание на январь, то указываем следующий год
                if curMonth == 12 and mamaMonth == 1:
                    quizDT = datetime.datetime(nextYear, mamaMonth, mamaDay, mamaHour, mamaMinute)
                else:
                    quizDT = datetime.datetime(curYear, mamaMonth, mamaDay, mamaHour, mamaMinute)

                if quizDT >= curDT:
                    games[orgTag + str(q)] = {}
                    games[orgTag + str(q)]['game'] = mamaGameName
                    games[orgTag + str(q)]['date'] = quizDT
                    games[orgTag + str(q)]['bar'] = mamaBar
                    games[orgTag + str(q)]['tag'] = mamaGameTag
        except Exception as err:
            organizatorErrors[mamaName] = str(err)
    return games, organizatorErrors


# функция которая делает фильтрацию по предпочтениям пользователя и преобразует список квизов в необходимый для вывода формат:
# 1. Квиз Плиз: [новички] NSK #416. Бар: Mishkin&Mishkin, суббота, 11 июня, 16:00
#входные параметры
# games: список всех доступных квизов, формируется в collectQuizData()
# organizatorErrors: список организаторов по которым не удалось получить информацию с сайта, формируется в collectQuizData(), эта информация выводится пользователю после сформированного списка игр
# dow: выбранный в ходе чата день проведения квиза (будни/ выходные/ любой)
# theme: выбранная в ходе чата тематика
# excl_bar: бары, которые нужно исключить из выборки, берется из пользовательских preferences
# excl_theme: какие тематики нужно исключить, берется из пользовательских preferences. актуальна когда в чате пользователь выбрал "любая тематика", чтобы в выводе не отображались неинтересные ему
# excl_orgs: каких организаторов нужно исключить, берется из пользовательских preferences

def createQuizList(games, organizatorErrors, dow, selected_theme, excl_bar, excl_theme, excl_orgs):
    # сортируем квизы разных вендоров по дате проведения
    dateList = []
    indexList = []
    quizList = []

    #формируем словарь вида {'qp': 'Квиз Плиз', 'li': 'Лига Индиго', 'mama': 'Мама Квиз', 'wow': 'WOW Quiz/ Эйнштейн Party'}, чтобы можно было извлекать название организатора по индексу
    organizatorIndexMapping = {}
    for curOrgName in organizatorsDict:
        curOrgIndex = organizatorsDict[curOrgName][0]
        organizatorIndexMapping[curOrgIndex] = curOrgName

    for quizIndex in games:
        indexList.append(quizIndex) #записываем индекс в отдельный массив, чтобы после сортировки по дате знать какой индекс соответствует этой дате
        curGameParams = games.get(quizIndex)     #вытаскиваем параметры по текущему индексу квиза, например qp1
        curGameDate = curGameParams.get('date')
        dateList.append(curGameDate)

    #сортируем список с индексами на основании того как мы бы отсортировали список с датами
    indexList = [indexList for _,indexList in sorted(zip(dateList, indexList))]

    #теперь в отсортированном порядке извлекаем из основного листа games информацию об играх
    k = 0 # это будет счётчик квизов попавших под фильтр, далее этот номер будет использоваться для создания голосовалки
    for i in indexList:
        # определяем организатора, если пользователь хочет его исключить - исключаем. подставляем корректное имя организатора для вывода
        # i это индекс вида li1, wow24, qp6, вытаскиваем regexp-ом часть без цифры и достаем название организатора из словаря organizatorIndexMapping
        orgIndexRegex = re.compile(r'^([a-zA-Z]+)(\d{1,})$')
        mo = orgIndexRegex.search(i)
        curOrgTag = mo[1] #тэг лежит на первой позиции, ([a-zA-Z]+)
        curOrgName = organizatorIndexMapping[curOrgTag]
        if curOrgName in excl_orgs:
            continue
        else:
            organizator = '<b>' + curOrgName + '</b>' #делаем форматирование, чтобы название организатора выводилось жирным шрифтом. '<b>Квиз Плиз</b>'

            # исключаем из выборки отмеченные пользователем бары. сравниваем в нижнем регистре
        if games[i]['bar'].lower() in excl_bar.lower():
            continue

        #оставляем только ту тематику, которую пользователь явно выбрал
        if selected_theme != themes[0] and selected_theme not in games[i]['tag']:
            continue
        #проверяем нет ли у игры доп. тематики, по которой ее все таки надо исключить. например, у игры тематики "Мультимедиа" и "Ностальгия"
        #пользователь выбрал Мультимедиа, а в исключениях у него Ностальгия. такую игру исключаем
        #также если пользователь выбрал "Оставить все", то исключаем те тематики которые он исключил в preferences
        #elif selected_theme != themes[0]:
        else:
            mainLoopState = False #для того чтобы прервать outer loop
            for t in games[i]['tag']:
                if t in excl_theme:
                    mainLoopState = True
                    break #прерываем inner loop
            if mainLoopState:
                continue

        #извлекаем информацию о дате, отбрасываем неподходящие дни если задан параметр dow, преобразуем дату в читаемый формат
        quizDate = games[i]['date']
        quizTime = quizDate.time()
        quizTime = quizTime.isoformat('minutes')    #время в формате HH:MM

        quizDOW = quizDate.isoweekday()
        if quizDOW in dow:
            k += 1
            #вытягиваем из словаря значение key по имеющемуся value
            #print(list(mydict.keys())[list(mydict.values()).index(16)])
            #https://stackoverflow.com/questions/8023306/get-key-by-value-in-dictionary
            quizMonth = list(MonthDict.keys())[list(MonthDict.values()).index(quizDate.month)]
            quizDOWReadable = dowDict[quizDOW]
            #приводим дату к читабельному виду "26 июня, 18:00"
            quizDateReadable = str(quizDate.day) + ' ' + quizMonth + ', ' + quizTime
            quizReadable = str(k) + '. ' + organizator + ': ' + games[i]['game'] + '. Бар: ' + games[i]['bar'] + ', ' + quizDOWReadable + ', ' + quizDateReadable + '\n'
            quizList.append(quizReadable)

    #если при запросе информации по каким-то организаторам были ошибки - выводим пользователю это сообщение
    if len(organizatorErrors) > 0:
        quizList.append('\nК сожалению не удалось получить информацию по следующим организаторам: ')
        for e in organizatorErrors:
            quizList.append(e)
        quizList.append('\nПопробуй запросить информацию по ним позже.')

    return quizList







