"""
Модуль операций с базой данных на основе SQLAlchemy.

Содержит функции:
    create_connection(dbPath) - создает подключение к БД (и файл БД при использовании SQLite)
    create_table(engine) - создает таблицы в БД
    get_user_preferences(conn, telegram_id) - делает SELECT запрос
    insert_new_user(conn, telegram_id, city, excl_bar, excl_theme, excl_org) - делает INSERT запрос
    update_user_preferences(conn, telegram_id, city, excl_bar, excl_theme, excl_org) - делает UPDATE запрос
    delete_user(conn, telegram_id) - делает DELETE запрос

Используемая документация:
https://www.tutorialspoint.com/sqlalchemy/sqlalchemy_quick_guide.htm#
https://docs.sqlalchemy.org/en/14/orm/queryguide.html#select-statements
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

import config
from config import logger

meta = MetaData()
userPreferences = Table(
    'user_preferences', meta,
    Column('telegram_id', Integer, unique=True, index=True),
    Column('city', String, index=True),
    Column('exclude_bar', String),
    Column('exclude_theme', String),
    Column('exclude_org', String),
)

def create_connection(dbPath = config.DBPATH):
    """
    Создает подключение к базе данных.
    Если в качестве СУБД используется SQLite, то создается локальный файл БД по адресу ./app_db/a4av.db. Если файл уже
    создан, осуществляется подключение к нему.
    :param dbPath (str): строка подключения к БД, по умолчанию задана в config.dbPath
    :return: tuple с объектами Engine и Connection, к-е используются как входные параметры в других функциях модуля.
    """

    # если используется SQLite: проверяем наличие всех нужных папок по пути к файлу БД, если их нет - создаём
    if 'sqlite' in dbPath:
        logger.debug(f'Запрос на создание connection до файла БД {dbPath} в родительском каталоге каталога {Path.cwd()}')
        lastSlashIndex = dbPath.rfind(r'/')
        dirLocation = dbPath[10:lastSlashIndex]  # отрезаем 'sqlite:///' и '/a4av.db', остается имя папки
        dirPath = Path.cwd() / dirLocation
        if not os.path.exists(dirPath):
            logger.debug(f'Создаем недостающие директории по пути {dirPath}')
            os.makedirs(dirPath)

    try:
        engine = create_engine(dbPath, echo = False)  #echo = True - вывод логов в консоль
        conn = engine.connect()
    except Exception as err:
        logger.error(f'Не удается создать create_engine по dbPath = {dbPath} с ошибкой {str(err)}')
        raise
    return engine, conn


def create_table(engine):
    """
    Создает таблицу из объекта Meta. По умолчанию на вход передается engine, сформированный при импорте функции
    engine, conn = create_connection().
    Для тестирования необходимо формировать новый engine и передавать его на вход.
    :param engine: объект класса Engine
    :return: None
    """
    logger.debug(f'Получен запрос на создание таблицы в файле БД в родительском каталоге каталога {Path.cwd()} ')
    try:
        meta.create_all(engine)
        logger.debug(f'Создана таблица {userPreferences.name}')
    except Exception as err:
        logger.error(f'Не удается создать таблицу user_preferences с ошибкой {str(err)}')


def get_user_preferences(conn, telegram_id):
    """
    Делает SELECT запрос предпочтений пользователя из БД.
    :param conn: подключение к БД
    :param telegram_id (int): идентификатор пользователя в Telegram
    :return: tuple вида (123456, 'Новосибирск', 'ART pub', '18+', 'mama quiz') либо None, если такого пользователя нет.
    """
    from sqlalchemy import select
    stmt = select(userPreferences).where(userPreferences.c.telegram_id == telegram_id)
    try:
        result = conn.execute(stmt)
        returnValue = result.fetchone()  # этой командой извлекаются результаты из объекта Result
        logger.debug(f'SELECT запрос по пользователю {telegram_id} вернул: {returnValue}')
        return returnValue
    except Exception as err:
        logger.error(f'SELECT запрос по пользователю {telegram_id} не удался со следующей ошибкой: {str(err)}')
        return None


def insert_new_user(conn, telegram_id, city, excl_bar, excl_theme, excl_org):
    """
    Функция для добавления нового пользователя и его предпочтений в БД с помощью INSERT запроса.
    :param conn: подключение к БД
    :param telegram_id (int): идентификатор пользователя в Telegram
    :param city (str): город
    :param excl_bar (str): перечень баров, которые пользователь хочет исключить из выборки
    :param excl_theme (str): перечень  тематик, которые пользователь хочет исключить из выборки
    :param excl_org (str): перечень  организаторов, которые пользователь хочет исключить из выборки
    :return: bool
    """
    from sqlalchemy import insert
    stmt = (
        insert(userPreferences).
        values
        (telegram_id=telegram_id,
         city=city,
         exclude_bar=excl_bar,
         exclude_theme=excl_theme,
         exclude_org=excl_org
         )
    )
    try:
        result = conn.execute(stmt)
        return True
    except Exception as err:
        logger.error(f'INSERT запрос по пользователю {telegram_id} не удался со следующей ошибкой: {str(err)}')
        return False


def update_user_preferences(conn, telegram_id, city, excl_bar, excl_theme, excl_org):
    """
    Функция для обновления предпочтений пользователя в БД с помощью UPDATE запроса.
    :param conn: подключение к БД
    :param telegram_id (int): идентификатор пользователя в Telegram
    :param city (str): город
    :param excl_bar (str): перечень баров, которые пользователь хочет исключить из выборки
    :param excl_theme (str): перечень  тематик, которые пользователь хочет исключить из выборки
    :param excl_org (str): перечень  организаторов, которые пользователь хочет исключить из выборки
    :return: bool
    """
    from sqlalchemy import update
    stmt = (update(userPreferences).
            where(userPreferences.c.telegram_id == telegram_id).
            values(
                city=city,
                exclude_bar=excl_bar,
                exclude_theme=excl_theme,
                exclude_org=excl_org
                )
            )
    try:
        result = conn.execute(stmt)
        return True
    except Exception as err:
        logger.error(f'UPDATE запрос по пользователю {telegram_id} не удался со следующей ошибкой: {str(err)}')
        return False


def delete_user(conn, telegram_id):
    """
    Функция для удаления пользователя из БД. На настоящий момент можно запустить функцию только вручную.
    :param conn: подключение к БД
    :param telegram_id (int): идентификатор пользователя в Telegram
    :return: bool
    """
    from sqlalchemy import delete
    stmt = (
        delete(userPreferences)
        .where(userPreferences.c.telegram_id == telegram_id)
    )
    try:
        result = conn.execute(stmt)
        return True
    except Exception as err:
        logger.error(f'DELETE запрос по пользователю {telegram_id} не удался со следующей ошибкой: {str(err)}')
        return False


if __name__ == '__main__':
    # Если требуется создать подключение, файл SQLite 'a4av.db' и таблицу user_preference в ручном режиме.
    # По умолчанию все это создается либо в telegramBot.py, либо в Unit-тестах.
    ENGINE, CONN = create_connection()
    create_table(ENGINE)