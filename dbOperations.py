#TODO:
#* добавить в telegramBot проверку создана ли таблица и если нет, то вызвать create_table()
#* проверить необходимость использование контекстного менеджера with при работе с engine и connection


#https://www.tutorialspoint.com/sqlalchemy/sqlalchemy_quick_guide.htm#
#https://docs.sqlalchemy.org/en/14/orm/queryguide.html#select-statements
import config
from config import logger, dbPath
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
import os
from pathlib import Path

meta = MetaData()
userPreferences = Table(
    'user_preferences', meta,
    Column('telegram_id', Integer, unique=True, index=True),
    Column('city', String, index=True),
    Column('exclude_bar', String),
    Column('exclude_theme', String),
    Column('exclude_org', String),
)
def create_connection(dbPath=config.dbPath):
    '''Функция create_connection() создает подключение к базе данных, строка подключения к БД задана в config.dbPath.
    Если в качестве СУБД используется SQLite, то создается локальный файл БД по адресу ./app_db/a4av.db.
    Если файл уже создан, осуществляется подключение к нему.'''

    # проверяем наличие всех нужных папок по пути к файлу БД, если их нет - создаём
    if 'sqlite' in dbPath:
        logger.debug(f'Запрос на создание connection до файла базы данных {dbPath} в каталоге {Path.cwd()}')
        lastSlashIndex = dbPath.rfind(r'/')
        dirLocation = dbPath[10:lastSlashIndex] # отрезаем 'sqlite:///' и '/a4av.db', остается имя папки
        dirPath = Path.cwd() / dirLocation
        if not os.path.exists(dirPath):
            logger.debug(f'Создаем недостающие директории по пути {dirPath}')
            os.makedirs(dirPath)

    try:
        engine = create_engine(dbPath, echo = False) #echo = True - вывод логов в консоль
        conn = engine.connect()
    except Exception as err:
        logger.error('Не удается создать create_engine по dbPath = %s с ошибкой %s', dbPath, str(err))
        raise
    return engine, conn

#функция для создания таблицы
def create_table(engine):
    '''Функция для создания таблиц из объекта Meta. По умолчанию на вход передается engine, сформированный при
    импорте функции (engine, conn = create_connection().
    Для тестирования необходимо формировать новый engine и передавать на вход его'''
    logger.debug(f'Получен запрос на создание таблицы в файле базы данных в папке {Path.cwd()} ')
    try:
        meta.create_all(engine)
        logger.debug(f'Создана таблица {userPreferences.name}')
    except Exception as err:
        logger.error('Не удается создать таблицу user_preferences с ошибкой %s', str(err))

#Запрос предпочтений пользователя, возвращает результат в формате (123456, 'Новосибирск', 'ART pub', '18+', 'mama quiz') либо None
def get_user_preferences(conn, telegram_id):
    from sqlalchemy import select
    stmt = select(userPreferences).where(userPreferences.c.telegram_id == telegram_id)
    try:
        result = conn.execute(stmt)
        returnValue = result.fetchone() #этой командой извлекаются результаты из объекта Result
        logger.debug("SELECT запрос по пользователю %s вернул: %s", telegram_id, returnValue)
        return returnValue
    except Exception as err:
        logger.error("SELECT запрос по пользователю %s не удался со следующей ошибкой: %s", telegram_id, str(err))
        return None

def insert_new_user(conn, telegram_id, city, excl_bar, excl_theme, excl_org):
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
        logger.error("INSERT запрос по пользователю %s не удался со следующей ошибкой: %s", telegram_id,str(err))
        return False

def update_user_preferences(conn, telegram_id, city, excl_bar, excl_theme, excl_org):
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
        logger.error("UPDATE запрос по пользователю %s не удался со следующей ошибкой: %s", telegram_id, str(err))
        return False

#на период тестов, в проде не предполагается функционала удаления пользователей
def delete_user(conn, telegram_id):
    from sqlalchemy import delete
    stmt = (
        delete(userPreferences)
        .where(userPreferences.c.telegram_id == telegram_id)
    )
    try:
        result = conn.execute(stmt)
        return True
    except Exception:
        logger.error("DELETE запрос по пользователю %s не удался со следующей ошибкой: %s", telegram_id, str(err))
        return False



if __name__ == '__main__':
    # в ручном режиме создаем подключение, файл SQLite 'a4av.db' и таблицу user_preference в нем
    ENGINE, CONN = create_connection()
    create_table(ENGINE)