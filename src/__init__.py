"""
Телеграм-бот, создающий список квизов, проходящих в Новосибирске.

Модули:
    config.py - конфигурация бота
    dbOperations.py - операции с базой данных
    quizAggregator.py - сбор и форматирование информации о проводимых квизах с сайтов организаторов
    secrets.py - пароли
    telegramBot.py - телеграм-бот, именно этот файл нужно запустить для работы программы
"""

# TODO LIST:

# в telegramBot.py при отправке списка квизов сделать ограничение по макс длине отправляемого сообщения
# когда 2023-02-22 делал запрос /all вернулось
# File "D:\Python\_dolgov\A4AV_bot\venv\lib\site-packages\telegram\request\_baserequest.py", line 328, in _request_wrapper
#    raise BadRequest(message)
# +telegram.error.BadRequest: Message is too long

# добавить Мозгобойню, Эйнштейн Пати, Угадай мелодию, Сибквиз, QuizClub, других оргов?

# придумать более надежный алгоритм скрейпинга Мама Квиз, в mamaquiz_schedule_2024-01-15.html неправильно парсится дата
# киномьюзик
