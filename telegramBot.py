#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.
#https://github.com/python-telegram-bot/python-telegram-bot/blob/v20.0a0/examples/conversationbot.py
#https://docs.python-telegram-bot.org/en/stable/examples.pollbot.html

#release notes
#0.1.2 - добавляем выбор квиза по тематике "классика"/ "КиМ"...
#GIT test

#change logs
#в первой версии использовали python-telegram-bot==20.0a0, там был синтаксис sendallquizzes(update: Update, context: CallbackContext.DEFAULT_TYPE)
#2023-01 обновились до версии 20.0, там синтаксис start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

from config import logger
#импортируем наш рукописный модуль который парсит квизы, фильтрует их и присылает нам готовый list со строками которые надо отправить пользователю
from quizAggregator import createInfoByCity, collectQuizData, createQuizList
from dbOperations import create_connection, insert_new_user, get_user_preferences, update_user_preferences

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
from config import themes

#это некие states которые используются далее в conv_handler, используются для навигации между функциями в зависимости от ввода пользователя
#эта строка должна совпадать со States в ConversationHandler функции __main__. Range прописывается вручную и должен соответствовать фактическому количеству states.
# состояния хэндлера
INLINE_KEYBOARD_STATE, SEND, SENDALL, PREFERENCES_CHOICE, EXCL_BAR_POLL, EXCL_BAR_RESULT, EXCL_THEME_POLL, EXCL_THEME_RESULT, EXCL_ORGANIZATORS_POLL, EXCL_ORGANIZATORS_RESULT = range(10)

city = 'Новосибирск' # пока задано хардкодом, на будущее предусмотрена возможность выбора города
                    #также не забыть перенести строку preferencesList[0] = city из функции excl_bar_result
quizList = [] #задаются как глобальные переменные чтобы можно было использовать в разных функциях
bars = []
organizators = []
links = []
preferencesList = []
queryResult = ''
games = {}
organizatorErrors = {}
#user is {'is_bot': False, 'username': 'v_dolgov', 'first_name': 'Vitaly', 'last_name': 'Dolgov', 'id': 1666680001, 'language_code': 'ru'}
DOW = [] #задается как глобальная переменная чтобы можно было использовать в разных функциях
DOWtext = '' #задается как глобальная переменная, здесь будет выбранный день недели
theme = '' #задается как глобальная переменная, здесь будет выбранная тематика квиза

#функция реагирующая на /start. здоровается и предлагает выбрать в какой день недели хотите сыграть
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("Начинаю чат с пользователем %s", user.id)
    reply_inline_keyboard=[
        [InlineKeyboardButton("Любой день сойдет", callback_data="Любой день сойдет")],
        [
            InlineKeyboardButton("Будни", callback_data="Будни"),
            InlineKeyboardButton("Выходные", callback_data="Выходные"),
        ]
    ]

    global preferencesList, queryResult
    queryResult = get_user_preferences(CONN, user.id)
    if queryResult: # делаем запрос о предпочтениях пользователя в БД, если он неуспешен то вернет None и не подпадет под условие
        preferencesList = list(queryResult) #БД возвращает tuple, переделываем его в List
    if preferencesList:
        await update.message.reply_text(
            f'Привет! Рад снова тебя видеть.\nВ какой день вы хотели бы сходить на игру?',
            reply_markup=InlineKeyboardMarkup(reply_inline_keyboard)
        )
    else:
        await update.message.reply_text(
        f'Привет!\nТы у нас в первый раз, предлагаю пройти короткий опрос, чтобы исключить из вывода неподходящие вам места проведения, '
        f'неинтересные тематики или нелюбимых организаторов. \nЧтобы пройти опрос отправь команду /preferences.'
        f'\n\nЛибо можем преступить к выбору сразу: в какой день вы бы хотели сходить на игру?',
        reply_markup=InlineKeyboardMarkup(reply_inline_keyboard),
    )

    return INLINE_KEYBOARD_STATE

async def chooseTheme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #это хэндлер типа CallbackQueryHandler для обработки ответов Inline клавиатуры, здесь пользователь и ответ достается иначе, чем в Message Handler
    """Записываем в глобальную переменную DOW выбранные дни недели для использования в других функциях"""
    query = update.callback_query
    await query.answer()
    user =  query.from_user
    reply_inline_keyboard = []
    global DOW, DOWtext
    DOWtext = query.data
    if DOWtext == "Будни":
        DOW = [1,2,3,4,5]
    elif DOWtext == "Выходные":
        DOW = [6,7]
    else:
        DOW = [1,2,3,4,5,6,7]

    logger.info("Пользователь %s выбрал день недели: %s", user.id, DOWtext)

    #предлагаем выбрать пользователю только те тематики, которые он не исключал в своих preferences
    #если он ничего не исключал, то вставляем полный список themes
    if preferencesList:
        themesCopy = themes.copy() #создаем копию списка, чтобы удалять элементы из нее
        exclThemes = preferencesList[3] # исключенные пользователем темы хранятся в виде 'Новички;18+'
        exclThemesList = exclThemes.split(';') #преобразуем исключенные темы в список
        for excl in exclThemesList: #для каждого исключения находим его индекс в исходном списке themes и удаляем его оттуда
            if excl in themesCopy:
                indexToDelete = themesCopy.index(excl)
                del themesCopy[indexToDelete]

        #формируем динамическую InlineKeyboard из доступных к выбору тематик
        #[[InlineKeyboardButton(callback_data='Оставить все', text='Оставить все')], [InlineKeyboardButton(callback_data='Классика', text='Классика')], [InlineKeyboardButton(callback_data='Мультимедиа', text='Мультимедиа')], [InlineKeyboardButton(callback_data='Ностальгия', text='Ностальгия')], [InlineKeyboardButton(callback_data='18+', text='18+')], [InlineKeyboardButton(callback_data='Новички', text='Новички')]]

        for i, button in enumerate(themesCopy):
            reply_inline_keyboard.append([InlineKeyboardButton(button, callback_data=button)])
        logger.info('Для пользователя %s сформировался следующий выбор тематик: %s', user.id, themesCopy)
    else:
        for i, button in enumerate(themes):
            reply_inline_keyboard.append([InlineKeyboardButton(button, callback_data=button)])
            logger.info('Для пользователя %s сформировался полный выбор тематик: %s', user.id, themes)
    await query.edit_message_text(
        "Есть предпочтения по тематике квиза?", reply_markup=InlineKeyboardMarkup(reply_inline_keyboard),
    )
    return INLINE_KEYBOARD_STATE

async def sendquiz_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # это хэндлер типа CallbackQueryHandler для обработки ответов Inline клавиатуры, здесь пользователь и ответ достается иначе, чем в Message Handler
    """Записываем в глобальную переменную DOW выбранные дни недели для использования в других функциях"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    global DOW, theme
    global DOWtext #текстовое название, для вывода пользователю информации какие фильтры он применил
    theme = query.data #текстовое название, для вывода в логи
    global quizList, games, organizatorErrors, bars, organizators, links, city, preferencesList
    # если в preferencesList нет значений, то вставляем дефолтные значения. Если значения есть, то предлагаем только те тематики, которры
    if not preferencesList:
        logger.info('Для пользователя %s еще нет значений preferenceList, присваиваем значения по умолчанию. Функция sendquiz_filtered', user.id)
        preferencesList = [user.id, city, 'None', 'None', 'None']
    quizTheme = query.data #тема квиза будет равна той кнопке, которую пользователь нажал в chooseTheme
    reply_end = 'Напоминаю, что согласно твоим предпочтениям часть игр могла быть скрыта из результатов поиска.\nОтправь команду /all если хочешь посмотреть полный список квизов.\nОтправь команду /preferences, чтобы изменить свои предпочтения.'
    logger.info("Пользователь %s выбрал следующую тематику: %s", user.id, theme)
    logger.info("Отправляю фильтрованный список квизов пользователю %s.", user.id)
    await query.edit_message_text(
        "Дай мне минутку на подготовку списка квизов.", parse_mode='HTML'
    )

    if not bars and not organizators and not links: #если по ходу работы чата эти переменные еще не были получены, то делаем запрос
        bars, organizators, links = createInfoByCity(city)

    telegramId, city, excl_bar, excl_theme, excl_orgs = preferencesList  # разбираем список на переменные для наглядности
    games, organizatorErrors = collectQuizData(organizators, links) #получаем список игр и список ошибок
    quizList = createQuizList(games, organizatorErrors, DOW, quizTheme, excl_bar, excl_theme, excl_orgs) #отдаем на вход список игр, желаемы дни проведения и тематику и получаем готовое текстовое сообщение с инфой о всех подходящих квизах
    if len(organizatorErrors) > 0:
        logger.error("Ошибка при запросах к следующим организаторам: " + str(organizatorErrors))
    logger.info("Запускаю для пользователя %s метод createQuizList с параметрами (%s, %s, %s, %s).", user.id, games, organizatorErrors, DOW, quizTheme)
    logger.debug("Список квизов для пользователя " + str(user.id) + ": " + str(quizList))
    if len(quizList) == 0:  #длина может быть = 0 только если ничего не нашлось и пришла строка про НИКТО НЕ ПРОВОДИТ
        reply_text = '<b>НИКТО</b> НЕ ПРОВОДИТ ТАКИХ КВИЗОВ!'
        logger.info("Для пользователя %s не вернулось ни одного квиза под данный фильтр", user.id)
    else:
        reply_text = f'<u>Вот квизы, которые пройдут в {DOWtext.lower()} по тематике {theme}:</u>\n'
        for i in range(len(quizList)):
            reply_text += quizList[i] + '\n'
        reply_text += '\nОтправь мне порядковый номер понравившейся игры и я создам голосовалку. Если дело происходит в группе, то ответь на мое сообщение, чтобы я понял что ты обращаещься ко мне. \n'
    reply_text += '\n' + reply_end

    await query.edit_message_text(
        reply_text, parse_mode='HTML'
    )

    return SEND

async def sendallquizzes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Функция которая отправляет полный список квизов, без фильтрации"""
    user = update.message.from_user
    DOW = [1,2,3,4,5,6,7]
    theme = themes[0] #берем нулевой элемент, 'Оставить все'
    logger.info("Отправляю полный список квизов пользователю %s.", user.id)
    global quizList, games, organizatorErrors, bars, organizators, links, city
    #для случая когда мы пришли не из sendquizzes и еще не делали запрос в collectQuizData()
    #если мы пришли из sendquiz_filtered и уже делали запрос, то не нужно повторно делать запрос - это приведет к задержке в работе бота
    if not bars and not organizators and not links:  # если по ходу работы чата эти переменные еще не были получены, то делаем запрос
        bars, organizators, links = createInfoByCity(city)

    if len(games) == 0 and len(organizatorErrors) == 0:
        logger.info("Пользователь %s еще не запрашивал поиск квизов с фильтрами, делаем запрос collectQuizData.", user.id)
        await update.message.reply_text(
            "Дай мне минутку на подготовку списка квизов.", reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        games, organizatorErrors = collectQuizData(organizators, links)
        if len(organizatorErrors) > 0:
            logger.error("Ошибка при запросах к следующим организаторам: " + str(organizatorErrors))
    quizList = createQuizList(games, organizatorErrors, DOW, theme, 'None', 'None', 'None') #отдаем на вход список игр, желаемы дни проведения и тематику и получаем готовое текстовое сообщение с инфой о всех подходящих квизах
    
    if len(quizList) == 0:  #длина может быть = 0 только если ничего не нашлось и пришла строка про НИКТО НЕ ПРОВОДИТ
        reply_text = 'ВООБЩЕ НИКТО НЕ ПРОВОДИТ КВИЗЫ В БЛИЖАЙШИЕ ДНИ!'
        logger.warning("Не вернулось ни одного квиза при запросе без фильтров для пользователя %s. Это потенциальная ошибка.", user.id)
    else:
        reply_text = '<u>Вот все квизы которые я нашел:</u>\n'
        for i in range(len(quizList)):
            reply_text += quizList[i] + '\n'
        reply_text += '\nОтправь мне порядковый номер понравившейся игры и я создам голосовалку. Если дело происходит в группе, то ответь на мое сообщение, чтобы я понял что ты обращаещься ко мне.\nПомни, что даже с отключенными фильтрами я не отображаю информацию о квизах, где есть запись только в резерв и о квизах участие в которых возможно только по приглашениям.'
    
    await update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
    return SENDALL

async def create_poll_on_selected_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    global quizList
    user = update.message.from_user
    logger.info("Пользователь %s отправил %s в качестве номера квиза", user.id, update.message.text)
    quizIndex = int(update.message.text) - 1 # минус 1 т.к лист считается с нуля, а список выданный пользователю с единицы
    if quizIndex in range(len(quizList)):
        #найдется строка вида '3. <b>WOW Quiz</b>: Угадай кино #17. Бар: Три Лося, воскресенье, 12 июня, 18:00'
        #строковыми переменными убираем оттуда лишнее
        quizInfo = quizList[quizIndex]
        quizInfo = quizInfo.replace('<b>', '')
        quizInfo = quizInfo.replace('</b>', '')
        dotIndex = quizInfo.find('.')
        quizInfo = quizInfo[dotIndex + 2:]
        
        questions = ["Иду", "Не иду", "Мнусь"]
        message = await context.bot.send_poll(
            update.effective_chat.id,
            quizInfo,
            questions,
            is_anonymous=False,
            allows_multiple_answers=True,
        )
        # Save some info about the poll the bot_data for later use in receive_poll_answer
        payload = {
            message.poll.id: {
                "questions": questions,
                "message_id": message.message_id,
                "chat_id": update.effective_chat.id,
                "answers": 0,
            }
        }
        logger.info("Пользователь %s создал опрос: %s.", user.id, quizInfo)
        await update.message.reply_text(
        'Хорошей игры! На сим откланиваюсь. Чтобы запустить меня заново нажми /start.', reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        context.bot_data.update(payload)
    else:
        await update.message.reply_text(
        'Такой цифры не было! Чтобы запустить меня заново нажми /start.' , reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        logger.info("Пользователь %s отправил неправильный аргумент %s в качестве порядкового номера квиза и мы с ним попрощались", user.id, update.message.text)
    return ConversationHandler.END

#стартовая страница изменения настроек
async def preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    global preferencesList
    if preferencesList:
        logger.info("Пользователь %s отправил команду /preferences. У него уже были настройки: %s.",
                    user.id, str(preferencesList))
        reply_keyboard = [["Да", "Нет"]]
        reply_text = 'На настоящий момент ты выбрал(а) город <b>' + preferencesList[1] + '</b> и исключил(а) из поиска: \nбары <b>' + preferencesList[2] + '</b>;\nтематики <b>'  + preferencesList[3] + '</b>;\nорганизаторов <b>' + preferencesList[4] + '</b>.\n\nХочешь внести изменения?'
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Хочешь внести изменения?"
        ), parse_mode='HTML')
    else:
        logger.info("Пользователь %s отправил команду /preferences. Ранее у него не было сохраненных настроек.",
                    user.id)
        reply_keyboard = [["Да", "Нет"]]
        reply_text = 'У тебя еще не настроены предпочтения. Хочешь исключить какие-то бары/ тематики/ организаторов из общего списка?'
        await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Что делаем с настройками?"
        ), parse_mode='HTML')
    return PREFERENCES_CHOICE

#первый этап настроек: получаем информацию по конкретному городу и создаем опрос по исключению баров
async def excl_bar_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bars, organizators, links
    bars, organizators, links = createInfoByCity(city)
    user = update.message.from_user
    poll_text = 'Выбери те бары, квизы в которых не будут показаны.'
    logger.debug("Предлагаем пользователю %s исключить бары из списка %s ", user.id, str(bars))
    message = await context.bot.send_poll(
        update.effective_chat.id,
        poll_text,
        bars,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    # Save some info about the poll the bot_data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": bars,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)
    return EXCL_BAR_POLL

#обрабатываем результаты запроса по исключению баров
#https://docs.python-telegram-bot.org/en/stable/telegram.poll.html
async def excl_bar_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.poll_answer.user
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    reply_keyboard = [['Выбрать тематики']]
    global city, preferencesList
    if not preferencesList: #если список пуст, то создаем его в нужном формате, сразу вставляя telegramId и city, оставшие фильтры по умолчанию отключены (None)
        preferencesList = [user.id, city, 'None', 'None', 'None']
    else:
        preferencesList[1] = city # пока добавляем захардкоженный city здесь, потом надо перенести в новую функцию
    selected_options = answer.option_ids #индексы выбранных пользователем вариантов ответов
    try:
        poll_options = answered_poll["questions"] #варианты ответов в списке вида ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки вверх']
        # this means this poll answer update is from an old poll, we can't do our answering then
    except KeyError:
        return

    # Close poll after one participants voted
    answered_poll["answers"] += 1
    await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])

    #команда Оставить все бары должна всегда быть первой в списке, тогда ее индекс будет = 0
    if 0 in selected_options:
        logger.info('Пользователь %s выбрал опцию "Оставить все бары"', user.id)
        preferencesList[2] = 'None'
        await context.bot.send_message(
            answered_poll["chat_id"],
            'Хорошо, оставляем в выборке все бары. Теперь жми "Выбрать тематики".',
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
        logger.info('Пользователь %s исключил следующие бары: %s', user.id, answer_string)
        preferencesList[2] = answer_string #записываем получившуюся строку вида 'Арт П.А.Б.;Типография;Руки вверх' в список предпочтений
        await context.bot.send_message(
            answered_poll["chat_id"],
            'Запомню твои предпочтения по барам. Теперь жми "Выбрать тематики".',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, )
        )
    return EXCL_BAR_RESULT

#второй этап настроек: создаем опрос по исключению тематик
async def excl_theme_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    poll_text = 'Выбери те тематики которые следует исключить из списка квизов.'
    logger.debug("Предлагаем пользователю %s исключить тематики из списка %s ", user.id, str(themes))
    message = await context.bot.send_poll(
        update.effective_chat.id,
        poll_text,
        themes,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    # Save some info about the poll the bot_data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": themes,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)
    return EXCL_THEME_POLL

#обрабатываем результаты запроса по исключению тематик
#https://docs.python-telegram-bot.org/en/stable/telegram.poll.html
async def excl_theme_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.poll_answer.user
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    reply_keyboard = [['Выбрать организаторов']]
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
        logger.info('Пользователь %s выбрал опцию "Оставить все тематики"', user.id)
        preferencesList[3] = 'None'
        await context.bot.send_message(
            answered_poll["chat_id"],
            'Ок, оставляем в выборке все тематики. Теперь жми "Выбрать организаторов".',
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
        logger.info('Пользователь %s исключил следующие тематики: %s', user.id, answer_string)
        preferencesList[3] = answer_string #записываем получившуюся строку вида 'Ностальгические;18+' в список предпочтений
        await context.bot.send_message(
            answered_poll["chat_id"],
            'Запомню твои предпочтения по тематикам. Теперь жми "Выбрать организаторов".',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, )
        )
    return EXCL_THEME_RESULT

#третий этап настроек: создаем опрос по исключению организаторов
async def excl_organizators_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    return EXCL_ORGANIZATORS_POLL

#обрабатываем результаты запроса по исключению организаторов
#https://docs.python-telegram-bot.org/en/stable/telegram.poll.html
async def excl_organizators_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    return EXCL_ORGANIZATORS_RESULT

#4 этап: сохраняем настройки в базу данных
async def save_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

async def badbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("Badbye. Прощаюсь с пользователем %s, так как он отправил неправильный аргумент %s", user.id, update.message.text)
    await update.message.reply_text(
        'Вы ввели что-то не то. Гудбай, молодой человек! Чтобы запустить меня заново нажми /start', reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
    )
    return ConversationHandler.END

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("Прощаюсь с пользователем %s, так как он успешно завершил обслуживание.", user.id)
    await update.message.reply_text(
        'Я закончил свою работу. Чтобы запустить меня заново нажми /start', reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
    )
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    from config import botToken
    application = Application.builder().token(botToken).build()

    # Add conversation handler with the states THEME, DOW and LOCATION
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            INLINE_KEYBOARD_STATE: [
                CallbackQueryHandler(chooseTheme, pattern="^(Будни|Выходные|Любой день сойдет)$"),
                CallbackQueryHandler(sendquiz_filtered, pattern="^(Оставить все|Классика|Мультимедиа|Ностальгия|18\+|Новички)$"),
            ],
            SEND: [MessageHandler(filters.Regex("^(\d|\d\d)$"), create_poll_on_selected_quiz),
                   MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            SENDALL: [MessageHandler(filters.Regex("^(\d|\d\d)$"), create_poll_on_selected_quiz),
                   MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            PREFERENCES_CHOICE: [MessageHandler(filters.Regex("^Да"), excl_bar_poll),
                                 MessageHandler(filters.Regex("^Нет"), start),
                                MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            # для выбора города сделать переход из PREFERENCES_CHOICES в новое состояние SELECT_CITY
            # не забыть убрать захардкоженное значение city = "Новосибирск"
            EXCL_BAR_POLL: [PollAnswerHandler(excl_bar_result),
                      MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCL_BAR_RESULT: [MessageHandler(filters.Regex("^Выбрать тематики"), excl_theme_poll),
                      MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCL_THEME_POLL: [PollAnswerHandler(excl_theme_result),
                            MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCL_THEME_RESULT: [MessageHandler(filters.Regex("^Выбрать организаторов"), excl_organizators_poll),
                              MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCL_ORGANIZATORS_POLL: [PollAnswerHandler(excl_organizators_result),
                              MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)],
            EXCL_ORGANIZATORS_RESULT: [MessageHandler(filters.Regex("^Завершить настройку"), save_preferences),
                   MessageHandler(filters.TEXT & ~filters.COMMAND, badbye)]
            },
        fallbacks=[CommandHandler("all", sendallquizzes), CommandHandler("bye", goodbye), CommandHandler("preferences", preferences)],
        allow_reentry=True, #для того чтобы можно было заново вернуться в entry_points
        per_chat=False #для того чтобы можно было обрабатывать ответы на опрос
    )
    application.add_handler(conv_handler)
    #application.add_handler(CallbackQueryHandler(button))
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    ENGINE, CONN = create_connection() # создаем объекты Engine и Connect к файлу базы данных
    main()
