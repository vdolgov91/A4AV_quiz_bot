"""
Модуль Telegram-бота на базе python-telegram-bot.
Получает запросы от пользователя, возвращает пользователю информацию о проводимых в его городе квизах.

Написан на основе примеров с github разработчиков python-telegram-bot:
# This program is dedicated to the public domain under the CC0 license
https://github.com/python-telegram-bot/python-telegram-bot/blob/v20.0a0/examples/conversationbot.py
#https://docs.python-telegram-bot.org/en/stable/telegram.poll.html
https://github.com/python-telegram-bot/python-telegram-bot/wiki/Storing-bot%2C-user-and-chat-related-data

TODO: дописать docstring про модули и классы
TODO: описать словами логику работы бота
"""
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    PollAnswerHandler
)

from config import logger, QUIZ_THEMES
from quizAggregator import create_info_by_city, collect_quiz_data, create_formatted_quiz_list
from dbOperations import create_connection, create_table, insert_new_user, get_user_preferences, update_user_preferences

# states которые используются в объекте conv_handler функции main() для навигации между пользовательскими функциями.
# функция возвращает свой state, хэндлер по фильтрам заданным для этого state анализирует ввод пользователя и на его
# основании принимает решение о дальнейшей маршрутизации чата.
INLINE_KEYBOARD_SENT_TO_USER = 0
QUIZ_LIST_SENT_TO_USER = 1
PREFERENCES_CHOICE_MENU = 2
EXCLUDE_BAR_POLL = 3
EXCLUDE_BAR_RESULT = 4
EXCLUDE_THEME_POLL = 5
EXCLUDE_THEME_RESULT = 6
EXCLUDE_ORGANIZATORS_POLL = 7
EXCLUDE_ORGANIZATORS_RESULT = 8

# город пока задан хардкодом, на будущее предусмотрена возможность выбора города пользователем
# при доработке нужно не забыть перенести строку preferencesList[0] = city из функции exclude_bar_result
city = 'Новосибирск'

# так как возможен разный порядок прохождения по веткам бота, то неизвестно была ли собрана нужная для работы текущей
# ветки информация. чтобы не делать повторяющиеся запросы в каждой ветке, запрос делается один раз и его результат
# сохранятеся в глобальные переменные. остальные функции берут данные из глобальных переменных, а не из повторного
# запроса
quizList = []
bars = []
organizators = []
links = []
preferencesList = []
queryResult = ''
games = {}
organizatorErrors = {}
DOW = []  # дни недели порядковыми номерами дня, для фильтрации списка квизов в модуле quizAggregator
DOWtext = ''  # дни недели словами, для вывода пользователю информации какие фильтры он применил
theme = ''

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Реакция на команду /start. Бот здоровается и предлагает выбрать в какой день недели хотите сыграть.
    :return: INLINE_KEYBOARD_SENT_TO_USER (int)
    """
    user = update.message.from_user
    logger.info(f'Начинаю чат с пользователем {user.id}')

    # подготавливаем inline-клавиатуру с вариантами ответа
    reply_inline_keyboard=[
        # в верхнем ряду находится одна inline-кнопка
        [InlineKeyboardButton('Любой день сойдет', callback_data='Любой день сойдет')],
        # в нижнем ряду находятся две inline-кнопки
        [InlineKeyboardButton('Будни', callback_data='Будни'),
        InlineKeyboardButton('Выходные', callback_data='Выходные'),
        ]
    ]

    global preferencesList, queryResult
    # делаем запрос о предпочтениях пользователя в БД, если он неуспешен, то вернет None
    queryResult = get_user_preferences(CONN, user.id)
    if queryResult:
        # БД возвращает tuple, переделываем его в List и сохраняем в глобальную переменную для дальнейшего использования
        preferencesList = list(queryResult)

    # отправляем пользователю приветственное сообщение и inline-клавиатуру с вариантами ответа
    # приветствие выбирается в зависимости от того есть ли в БД информация о пользователе
    if preferencesList:
        await update.message.reply_text(
            f'Привет! Рад снова тебя видеть.\nВ какой день вы хотели бы сходить на игру?',
            reply_markup=InlineKeyboardMarkup(reply_inline_keyboard)
        )
    else:
        await update.message.reply_text(
        f'Привет!\nТы у нас в первый раз, предлагаю пройти короткий опрос, чтобы исключить из вывода неподходящие вам '
        f'места проведения, неинтересные тематики или нелюбимых организаторов. \nЧтобы пройти опрос отправь команду '
        f'/preferences.\n\nЛибо можем преступить к выбору сразу: в какой день вы бы хотели сходить на игру?',
        reply_markup=InlineKeyboardMarkup(reply_inline_keyboard),
    )

    return INLINE_KEYBOARD_SENT_TO_USER


async def choose_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ответ пользователя на приветственное сообщение, выбранный из вариантов inline-клавиатуры.
    Предлагает пользователю выбрать тематику квизов.
    :return: INLINE_KEYBOARD_SENT_TO_USER (int)
    """

    # ждём ответа пользователя
    query = update.callback_query
    await query.answer()
    user =  query.from_user

    reply_inline_keyboard = []

    # Записываем в глобальные переменные DOW и DOWtext выбранные дни недели для использования в других функциях
    global DOW, DOWtext
    DOWtext = query.data
    if DOWtext == 'Будни':
        DOW = [1,2,3,4,5]
    elif DOWtext == 'Выходные':
        DOW = [6,7]
    else:
        DOW = [1,2,3,4,5,6,7]

    logger.info(f'Пользователь {user.id} выбрал день недели: {DOWtext}')

    # предлагаем пользователю выбрать интересующую его тематику из списка config.QUIZ_THEMES
    # если в /preferences пользователя есть исключенные тематики, то исключаем их из вывода
    themesCopy = QUIZ_THEMES.copy()  # создаем копию списка, чтобы при необходимости удалять элементы из него
    if preferencesList:
        exclThemes = preferencesList[3]
        exclThemesList = exclThemes.split(';')
        # удаляем из списка themesCopy исключенные тематики, предварительно узнав их индекс в списке
        for excl in exclThemesList:
            if excl in themesCopy:
                indexToDelete = themesCopy.index(excl)
                del themesCopy[indexToDelete]

    # формируем из доступных к выбору тематик динамическую InlineKeyboard вида:
    # [[InlineKeyboardButton('Оставить все', callback_data='Оставить все')],
    # [InlineKeyboardButton('Классика', callback_data='Классика')],
    # [InlineKeyboardButton('Мультимедиа', callback_data='Мультимедиа')]]
    for i, button in enumerate(themesCopy):
        reply_inline_keyboard.append([InlineKeyboardButton(button, callback_data=button)])
    logger.info(f'Для пользователя {user.id} сформировался следующий список тематик для выбора: {themesCopy}')

    # отправляем пользователю сообщение и inline-клавиатуру с вариантами тематик
    await query.edit_message_text(
        'Есть предпочтения по тематике квиза?', reply_markup=InlineKeyboardMarkup(reply_inline_keyboard),
    )
    return INLINE_KEYBOARD_SENT_TO_USER


async def send_filtered_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ответ пользователя на вопрос о тематике квиза, выбранный из вариантов inline-клавиатуры.
    Отправляет пользователю отфильтрованный список квизов, с учетом выбранных им в ходе чата днях проведения и
    тематики, а также перманентных исключениях по тематикам/ организаторам/ барам, указанных в /preferences.
    :return: QUIZ_LIST_SENT_TO_USER (int)
    """
    global DOW, DOWtext, theme, quizList, games, organizatorErrors, bars, organizators, links, city, preferencesList

    # ждём ответа пользователя и сохраняем его
    query = update.callback_query
    await query.answer()
    user = query.from_user
    theme = query.data

    # если у пользователя еще нет /preferences, то присваиваем дефолтные значения - не исключаем из вывода ничего
    if not preferencesList:
        logger.info(f'Для пользователя {user.id} еще нет значений preferenceList, присваиваем значения по умолчанию. '
                    f'Функция send_filtered_quiz')
        preferencesList = [user.id, city, 'None', 'None', 'None']

    logger.info(f'Пользователь {user.id} выбрал следующую тематику: {theme}')
    logger.info(f'Готовлю фильтрованный список квизов пользователю {user.id}.')

    # так как скрейпинг сайтов с расписаниями квизов занимает порядка 10 секунд, то выводим пользователю сообщение с
    # просьбой подождать, чтобы он не думал что бот завис. Оно исчезнет, когда бот пришлет расписание квизов.
    await query.edit_message_text(
        'Дай мне минутку на подготовку списка квизов.', parse_mode='HTML'
    )

    # если в ходе работы бота значения переменных с информацией, специфической для города проведения еще не были
    # получены, то запрашиваем их
    if not bars and not organizators and not links:
        bars, organizators, links = create_info_by_city(city)

    # получаем полный неформатированный список квизов и список ошибок по отдельным организаторам
    games, organizatorErrors = collect_quiz_data(organizators, links)
    if len(organizatorErrors) > 0:
        logger.error(f'Ошибка при запросах к следующим организаторам: {organizatorErrors}')

    # получаем фильтрованный форматированный для вывода бота список квизов, с учетом выбора пользователя в ходе чата
    # (желаемые дни проведения, интересующая тематика) и перманентых /preferences пользователя (какие бары, тематики и
    # организаторов нужно исключать из вывода всегда)
    telegramId, city, excl_bar, excl_theme, excl_orgs = preferencesList
    logger.debug(f'Запускаю для пользователя {user.id} метод create_formatted_quiz_list с параметрами (games:{games}, '
                f'organizatorErrors: {organizatorErrors}, DOW: {DOW}, selected_theme: {theme}, excl_bar: {excl_bar}, '
                f'excl_theme: {excl_theme}, excl_orgs: {excl_orgs}.')
    quizList = create_formatted_quiz_list(games, organizatorErrors, dow=DOW, selected_theme=theme,
                                          excl_bar=excl_bar, excl_theme=excl_theme, excl_orgs=excl_orgs)
    logger.debug(f'Список квизов для пользователя {user.id}: {quizList}')

    # формируем сообщение для отправки пользователю, в зависимости от количества найденных квизов
    # текст отформатирован с использованием HTML-разметки.
    # TODO: существует ограничение по количеству символов, добавить обработку этой ситуации
    if len(quizList) == 0:
        reply_text = '<b>НИКТО</b> НЕ ПРОВОДИТ ТАКИХ КВИЗОВ!'
        logger.info(f'Для пользователя {user.id} не вернулось ни одного квиза под данный фильтр')
    else:
        reply_text = f'<u>Вот квизы, которые пройдут в {DOWtext.lower()} по тематике {theme}:</u>\n'
        for i, curQuiz in enumerate(quizList):
            reply_text += curQuiz + '\n'
        reply_text += '\nОтправь мне порядковый номер понравившейся игры и я создам голосовалку. Если дело ' \
                      'происходит в группе, то ответь на мое сообщение, чтобы я понял что ты обращаещься ко мне. \n'
    reply_end = 'Напоминаю, что согласно твоим предпочтениям часть игр могла быть скрыта из результатов поиска.\n' \
                'Отправь команду /all если хочешь посмотреть полный список квизов.\nОтправь команду /preferences, ' \
                'чтобы изменить свои предпочтения.'
    reply_text += '\n' + reply_end

    # отправляем пользователю сообщение с отфильтрованным списком квизов
    await query.edit_message_text(
        reply_text, parse_mode='HTML'
    )

    return QUIZ_LIST_SENT_TO_USER


async def send_all_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Реакция на команду /all.
    Отправляет пользователю полный список найденных квизов, без учетов выбраных в ходе чата дней недели/ тематики и
    перманентных настроек пользователя по исключению баров/ тематик/ организаторов из /preferences.
    Из вывода исключаются только квизы на которые нет мест и игры по приглашению (инвайту).
    :return: QUIZ_LIST_SENT_TO_USER (int)
    """
    global quizList, games, organizatorErrors, bars, organizators, links, city

    user = update.message.from_user
    logger.info(f'Отправляю полный список квизов пользователю {user.id}.')

    # если в ходе работы бота значения переменных с информацией, специфической для города проведения, еще не были
    # получены, то запрашиваем их
    if not bars and not organizators and not links:
        bars, organizators, links = create_info_by_city(city)

    # если бот уже был в функции send_filtered_quiz и делал скрейпинг сайтов организаторов функцией collect_quiz_data,
    # то не делаем эту операцию повторно.
    if not games and not organizatorErrors:
        logger.info(f'Пользователь {user.id} еще не запрашивал поиск квизов с фильтрами, делаем запрос '
                    f'collect_quiz_data().')
        # так как скрейпинг сайтов с расписаниями квизов занимает порядка 10 секунд, то выводим пользователю сообщение с
        # просьбой подождать, чтобы он не думал что бот завис. Оно исчезнет, когда бот пришлет расписание квизов.
        await update.message.reply_text(
            'Дай мне минутку на подготовку списка квизов.', reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        # получаем полный неформатированный список квизов и список ошибок по отдельным организаторам
        games, organizatorErrors = collect_quiz_data(organizators, links)
        if len(organizatorErrors) > 0:
            logger.error(f'Ошибка при запросах к следующим организаторам: {organizatorErrors}')

    # получаем форматированный для вывода бота полный список квизов
    # задаем значения переменных исключающих любую фильтрацию
    DOW = [1, 2, 3, 4, 5, 6, 7]
    theme = QUIZ_THEMES[0]  # 'Оставить все'
    quizList = create_formatted_quiz_list(games, organizatorErrors, dow=DOW, selected_theme=theme,
                                          excl_bar='None', excl_theme='None', excl_orgs='None')

    # формируем сообщение для отправки пользователю, в зависимости от количества найденных квизов
    # текст отформатирован с использованием HTML-разметки.
    # TODO: существует ограничение по количеству символов, добавить обработку этой ситуации
    if len(quizList) == 0:
        reply_text = 'ВООБЩЕ НИКТО НЕ ПРОВОДИТ КВИЗЫ В БЛИЖАЙШИЕ ДНИ!'
        logger.warning(f'Не вернулось ни одного квиза при запросе без фильтров для пользователя {user.id}. Это '
                       f'потенциальная ошибка.')
    else:
        reply_text = '<u>Вот все квизы которые я нашел:</u>\n'
        for i, curQuiz in enumerate(quizList):
            reply_text += curQuiz + '\n'
        reply_text += '\nОтправь мне порядковый номер понравившейся игры и я создам голосовалку. Если дело происходит ' \
                      'в группе, то ответь на мое сообщение, чтобы я понял что ты обращаещься ко мне.\nПомни, что ' \
                      'даже с отключенными фильтрами я не отображаю информацию о квизах, где есть запись только ' \
                      'в резерв и о квизах участие в которых возможно только по приглашениям.'

    # отправляем пользователю сообщение с отфильтрованным списком квизов
    await update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')

    return QUIZ_LIST_SENT_TO_USER


async def create_poll_on_selected_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Реакция на ввод пользоватем порядкового номера квиза из сформированного списка.
    Создает опрос по выбранному квизу и завершает работу бота.
    :return: ConversationHandler.END
    """
    global quizList

    # извлекаем информацию из ответа пользователя
    user = update.message.from_user
    logger.info(f'Пользователь {user.id} отправил {update.message.text} в качестве номера квиза')

    # на вход функции пропускается любое число из одного или двух символов (^(\d|\d\d)$)
    # проверяем что пользователь ввел корректный номер квиза.
    # например, если пользователю вывели 10 квизов, то введенное им число должно быть от 1 до 10.
    # пользователь выбирал индекс из диапазона 1:N, а в list диапазон индексов 0:N, поэтому вычитаем 1
    quizIndex = int(update.message.text) - 1
    if quizIndex in range(len(quizList)):
        # формируем заголовок опроса. убираем HTML-тэги и порядковый номер игры из строки вида
        # '3. <b>WOW Quiz</b>: Угадай кино #17. Бар: Три Лося, воскресенье, 12 июня, 18:00'
        # получаем строку вида:
        # 'WOW Quiz: Угадай кино #17. Бар: Три Лося, воскресенье, 12 июня, 18:00'
        quizInfo = quizList[quizIndex]
        quizInfo = quizInfo.replace('<b>', '')
        quizInfo = quizInfo.replace('</b>', '')
        dotIndex = quizInfo.find('.')
        quizInfo = quizInfo[dotIndex + 2:]

        # варианты ответов в опросе
        questions = ["Иду", "Не иду", "Мнусь"]

        # создаем опрос, не анонимный, множественный выбор отсутствует
        # результаты опроса бот не обрабатывает
        message = await context.bot.send_poll(
            update.effective_chat.id,
            quizInfo,
            questions,
            is_anonymous=False,
            allows_multiple_answers=False,
        )
        logger.info(f'Пользователь {user.id} создал опрос: {quizInfo}.')

        # отправляем пользователю сообщение об окончании работы бота
        await update.message.reply_text(
        'Хорошей игры! На сим откланиваюсь. Чтобы запустить меня заново нажми /start.',
            reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')

    else:
        # отправляем пользователю сообщение об окончании работы бота
        await update.message.reply_text(
        'Такой цифры не было! Чтобы запустить меня заново нажми /start.',
            reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        logger.info(f'Пользователь {user.id} отправил неправильный аргумент {update.message.text} в качестве '
                    f'порядкового номера квиза и мы с ним попрощались')

    return ConversationHandler.END


async def preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Реакция на команду /preferences.
    Выводит пользователю его текущие предпочтения (если они настроены) и предлагает изменить их.
    :return: PREFERENCES_CHOICE_MENU (int)
    """
    global preferencesList
    user = update.message.from_user

    if preferencesList:
        logger.info(f'Пользователь {user.id} отправил команду /preferences. У него уже были настройки: '
                    f'{preferencesList}.')
        reply_text = f'На настоящий момент ты выбрал(а) город <b>{preferencesList[1]}</b> и исключил(а) из ' \
                     f'поиска: \nбары <b>{preferencesList[2]}</b>;\n' \
                     f'тематики <b>{preferencesList[3]}</b>;\n' \
                     f'организаторов <b>{preferencesList[4]}</b>.\n\nХочешь внести изменения?'
    else:
        logger.info(f'Пользователь {user.id} отправил команду /preferences. Ранее у него не было сохраненных настроек.')
        reply_text = 'У тебя еще не настроены предпочтения. Хочешь исключить какие-то бары/ тематики/ организаторов ' \
                     'из общего списка?'

    # отправляем пользователю сообщение и inline-клавиатуру с вариантами Да/ Нет
    reply_keyboard = [["Да", "Нет"]]
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Хочешь внести изменения?"
        ), parse_mode='HTML')

    return PREFERENCES_CHOICE_MENU


async def exclude_bar_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Первый шаг настройки предпочтений пользователя по команде /preferences.
    Создает опрос, позволяющий перманентно исключать из выборки квизы, которые проводятся в определенных барах.
    :return EXCLUDE_BAR_POLL:
    """
    global bars, organizators, links, city
    # если в ходе работы бота значения переменных с информацией, специфической для города проведения еще не были
    # получены, то запрашиваем их
    if not bars and not organizators and not links:
        bars, organizators, links = create_info_by_city(city)

    user = update.message.from_user
    logger.debug(f'Предлагаем пользователю {user.id} исключить бары из списка {bars}')

    # создаем опрос, не анонимный, с множественным выбором, в качестве возможных ответов - бары из списка bars
    poll_text = 'Выбери те бары, квизы в которых не будут показаны.'
    message = await context.bot.send_poll(
        update.effective_chat.id,
        poll_text,
        bars,
        is_anonymous=False,
        allows_multiple_answers=True,
    )

    # сохраняем контекстную информацию о созданном опросе для дальнейшего использования
    payload = {
        message.poll.id: {
            "questions": bars,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)

    return EXCLUDE_BAR_POLL


async def exclude_bar_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает результаты опроса по исключению баров, пройденного пользователем.
    :return: EXCLUDE_BAR_RESULT (int)
    """
    global city, preferencesList
    if not preferencesList:
        preferencesList = [user.id, city, 'None', 'None', 'None']
    else:
        preferencesList[1] = city  # пока добавляем захардкоженный city здесь, потом надо перенести в новую функцию

    # получаем информацию о результатах опроса
    user = update.poll_answer.user
    selected_options = update.poll_answer.option_ids  # индексы выбранных пользователем вариантов ответов
    answered_poll = context.bot_data[update.poll_answer.poll_id]  # id опроса

    # обработка ошибки, когда пользователь ответил на какой-то старый опрос вместо нужного. дословно из примера:
    # this means this poll answer update is from an old poll, we can't do our answering then
    try:
        poll_options = answered_poll["questions"]  # варианты ответов из пройденного опроса
    except KeyError:
        debug.error(f'Ошибка обработки результатов опроса по барам у пользователя {user.id}')
        return

    # увеличиваем счётчик проголосовавших и закрываем опрос
    answered_poll["answers"] += 1
    await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])
    
    # создаем единственный вариант ответа для перехода на следующий этап настроек предпочтений
    reply_keyboard = [['Выбрать тематики']]
    
    # вариант 'Оставить все бары' хранится на нулевом индексе списка, если он был выбран, то ничего не исключаем
    if 0 in selected_options:
        logger.info(f'Пользователь {user.id} выбрал опцию "Оставить все бары"')
        preferencesList[2] = 'None'
        reply_text = 'Хорошо, оставляем в выборке все бары. Теперь жми "Выбрать тематики".'
    else:
        excluded_bars = ""
        for option_id in selected_options:
            #  чтобы не ставить ; после последнего из баров
            if option_id != selected_options[-1]:
                excluded_bars += poll_options[option_id] + ";"
            else:
                excluded_bars += poll_options[option_id]
        logger.info(f'Пользователь {user.id} исключил следующие бары: {excluded_bars}')
        # записываем получившуюся строку вида 'Арт П.А.Б.;Типография;Руки вверх' в список предпочтений
        preferencesList[2] = excluded_bars 
        reply_text = 'Запомню твои предпочтения по барам. Теперь жми "Выбрать тематики".'

    # отправляем пользователю сообщение
    await context.bot.send_message(
            answered_poll["chat_id"],
            reply_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
    
    return EXCLUDE_BAR_RESULT


async def exclude_theme_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Второй шаг настройки предпочтений пользователя по команде /preferences.
    Создает опрос, позволяющий перманентно исключать из выборки квизы неинтересных пользователю тематик.
    :return: EXCLUDE_THEME_POLL (int)
    """
    global QUIZ_THEMES

    user = update.message.from_user
    logger.debug(f'Предлагаем пользователю {user.id} исключить тематики из списка {QUIZ_THEMES}')

    # создаем опрос, не анонимный, с множественным выбором, в качестве возможных ответов - тематики из QUIZ.themes
    poll_text = 'Выбери те тематики которые следует исключить из списка квизов.'
    message = await context.bot.send_poll(
        update.effective_chat.id,
        poll_text,
        QUIZ_THEMES,
        is_anonymous=False,
        allows_multiple_answers=True,
    )

    # сохраняем контекстную информацию о созданном опросе для дальнейшего использования
    payload = {
        message.poll.id: {
            "questions": QUIZ_THEMES,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)

    return EXCLUDE_THEME_POLL


async def exclude_theme_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает результаты опроса по исключению тематик, пройденного пользователем.
    :return: EXCLUDE_THEME_RESULT (int)
    """
    global preferencesList

    # получаем информацию о результатах опроса
    user = update.poll_answer.user
    selected_options = update.poll_answer.option_ids  # индексы выбранных пользователем вариантов ответов
    answered_poll = context.bot_data[update.poll_answer.poll_id]  # id опроса

    # обработка ошибки, когда пользователь ответил на какой-то старый опрос вместо нужного. дословно из примера:
    # this means this poll answer update is from an old poll, we can't do our answering then
    try:
        poll_options = answered_poll["questions"]  # варианты ответов из пройденного опроса
    except KeyError:
        debug.error(f'Ошибка обработки результатов опроса по тематикам у пользователя {user.id}')
        return

    # увеличиваем счётчик проголосовавших и закрываем опрос
    answered_poll["answers"] += 1
    await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])

    # создаем единственный вариант ответа для перехода на следующий этап настроек предпочтений
    reply_keyboard = [['Выбрать организаторов']]

    # вариант 'Оставить все тематики' хранится на нулевом индексе списка, если он был выбран, то ничего не исключаем
    if 0 in selected_options:
        logger.info(f'Пользователь {user.id} выбрал опцию "Оставить все тематики"')
        preferencesList[3] = 'None'
        reply_text = 'Ок, оставляем в выборке все тематики. Теперь жми "Выбрать организаторов".'
    else:
        excluded_themes = ""
        for option_id in selected_options:
            #  чтобы не ставить ; после последнего из тематик
            if option_id != selected_options[-1]:
                excluded_themes += poll_options[option_id] + ";"
            else:
                excluded_themes += poll_options[option_id]
        logger.info(f'Пользователь {user.id} исключил следующие тематики: {excluded_themes}')
        # записываем получившуюся строку вида 'Ностальгические;18+' в список предпочтений
        preferencesList[3] = excluded_themes
        reply_text = 'Запомню твои предпочтения по тематикам. Теперь жми "Выбрать организаторов".'

    # отправляем пользователю сообщение
    await context.bot.send_message(
        answered_poll["chat_id"],
        reply_text,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return EXCLUDE_THEME_RESULT

#третий этап настроек: создаем опрос по исключению организаторов
async def exclude_organizators_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global organizators
    user = update.message.from_user
    poll_text = 'Выбери организаторов, чьи игры следует исключить из списка.'
    logger.debug("Предлагаем пользователю %s исключить организаторов из списка %s ", user.id, str(organizators))
    message = await context.bot.send_poll(
        update.effective_chat.id,
        poll_text,
        organizators,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    # Save some info about the poll the bot_data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": organizators,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)
    return EXCLUDE_ORGANIZATORS_POLL

#обрабатываем результаты запроса по исключению организаторов
#https://docs.python-telegram-bot.org/en/stable/telegram.poll.html
async def exclude_organizators_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.poll_answer.user
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    reply_keyboard = [['Завершить настройку']]
    global preferencesList
    selected_options = answer.option_ids #индексы выбранных пользователем вариантов ответов
    try:
        poll_options = answered_poll["questions"] #варианты ответов в списке вида ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки вверх']
        # this means this poll answer update is from an old poll, we can't do our answering then
    except KeyError:
        return

    # Close poll after one participants voted
    answered_poll["answers"] += 1
    await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])

    #команда Оставить все тематики должна всегда быть первой в списке, тогда ее индекс будет = 0
    if 0 in selected_options:
        logger.info('Пользователь %s выбрал опцию "Оставить всех организаторов"', user.id)
        preferencesList[4] = 'None'

        await context.bot.send_message(
            answered_poll["chat_id"],
            'Оставляю в выборке всех организаторов. Теперь жми "Завершить настройку".',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,)
        )
    else:
        answer_string = ""
        for option_id in selected_options:
            #условие чтобы не ставить ; после последнего из баров
            if option_id != selected_options[-1]:
                answer_string += poll_options[option_id] + ";"
            else:
                answer_string += poll_options[option_id]
        logger.info('Пользователь %s исключил следующих организаторов: %s', user.id, answer_string)
        preferencesList[4] = answer_string #записываем получившуюся строку вида 'Ностальгические;18+' в список предпочтений
        await context.bot.send_message(
            answered_poll["chat_id"],
            'Запомню твои предпочтения по организаторам. Теперь жми "Завершить настройку".',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, )
        )
    return EXCLUDE_ORGANIZATORS_RESULT

#4 этап: сохраняем настройки в базу данных
async def save_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    global preferencesList, queryResult
    telegramId, city, excl_bar, excl_theme, excl_orgs = preferencesList #разбираем список на переменные для наглядности

    #если queryResult что-то вернул, то надо делать UPDATE. если не вернул - то INSERT
    if queryResult:
        # при удачном апдейте функция возвращает True, при неудачной False
        if update_user_preferences(CONN, user.id, city, excl_bar, excl_theme, excl_orgs):
            logger.info('Пользователь %s обновил свои предпочтения', user.id)
            await update.message.reply_text(
                'Твои настройки обновлены! Теперь нажми команду /start, чтобы приступить к поиску квизов.',
                reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
            )
        else:
            logger.error('Пользователь %s не смог обновить свои предпочтения', user.id)
            await update.message.reply_text(
                'К сожалению сейчас не удается обновить твои настройки, попробуй позже.\nЧтобы приступить к поиску квизов нажми команду /start.',
                reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
            )

    else:
        #при удачной вставке функция возвращает True, при неудачной False
        if insert_new_user(CONN, user.id, city, excl_bar, excl_theme, excl_orgs):
            logger.info('Пользователь %s сохранил свои предпочтения в базу данных', user.id)
            await update.message.reply_text(
                'Твои настройки сохранены! Теперь нажми команду /start, чтобы приступить к поиску квизов.',
                reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
            )
        else:
            logger.error('Пользователь %s не смог сохранить свои предпочтения в базу данных', user.id)
            await update.message.reply_text(
                'К сожалению сейчас не удается сохранить твои настройки, попробуй позже.\nЧтобы приступить к поиску квизов нажми команду /start.',
                reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
            )

async def badbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("Badbye. Прощаюсь с пользователем %s, так как он отправил неправильный аргумент %s", user.id, update.message.text)
    await update.message.reply_text(
        'Вы ввели что-то не то. Гудбай, молодой человек! Чтобы запустить меня заново нажми /start', reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
    )
    return ConversationHandler.END

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("Прощаюсь с пользователем %s, так как он успешно завершил обслуживание.", user.id)
    await update.message.reply_text(
        'Я закончил свою работу. Чтобы запустить меня заново нажми /start', reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
    )
    return ConversationHandler.END

def main():
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    from config import BOT_TOKEN
    application = Application.builder().token(BOT_TOKEN).build()

    # Add conversation handler with the states THEME, DOW and LOCATION
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            INLINE_KEYBOARD_SENT_TO_USER: [
                CallbackQueryHandler(choose_theme, pattern="^(Будни|Выходные|Любой день сойдет)$"),
                CallbackQueryHandler(send_filtered_quiz,
                                     pattern="^(Оставить все|Классика|Мультимедиа|Ностальгия|18\+|Новички)$"),
            ],
            QUIZ_LIST_SENT_TO_USER: [MessageHandler(filters.Regex("^(\d|\d\d)$"), create_poll_on_selected_quiz),
                                     MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            PREFERENCES_CHOICE_MENU: [MessageHandler(filters.Regex("^Да"), exclude_bar_poll),
                                      MessageHandler(filters.Regex("^Нет"), start),
                                      MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            # для выбора города сделать переход из PREFERENCES_CHOICES в новое состояние SELECT_CITY
            # не забыть убрать захардкоженное значение city = "Новосибирск"
            EXCLUDE_BAR_POLL: [PollAnswerHandler(exclude_bar_result),
                               MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCLUDE_BAR_RESULT: [MessageHandler(filters.Regex("^Выбрать тематики"), exclude_theme_poll),
                                 MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCLUDE_THEME_POLL: [PollAnswerHandler(exclude_theme_result),
                                 MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCLUDE_THEME_RESULT: [MessageHandler(filters.Regex("^Выбрать организаторов"), exclude_organizators_poll),
                                   MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCLUDE_ORGANIZATORS_POLL: [PollAnswerHandler(exclude_organizators_result),
                                        MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCLUDE_ORGANIZATORS_RESULT: [MessageHandler(filters.Regex("^Завершить настройку"), save_preferences),
                                          MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)]
            },
        fallbacks=[CommandHandler("all", send_all_quizzes), CommandHandler("bye", goodbye),
                   CommandHandler("preferences", preferences)],
        allow_reentry=True,  # для того чтобы можно было заново вернуться в entry_points
        per_chat=False  # для того чтобы можно было обрабатывать ответы на опрос
    )
    application.add_handler(conv_handler)
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    ENGINE, CONN = create_connection()  # создаем объекты Engine и Connect к базе данных
    create_table(ENGINE)  # создаем нужные таблицы (если еще не были созданы)
    main()
