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
# добавить Мозгобойню, Эйнштейн Пати, Угадай мелодию, Сибквиз, QuizClub, других оргов?

# придумать более надежный алгоритм скрейпинга Мама Квиз, в mamaquiz_schedule_2024-01-15.html неправильно парсится дата
# киномьюзик
