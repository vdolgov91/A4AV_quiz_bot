#https://www.tutorialspoint.com/sqlalchemy/sqlalchemy_quick_guide.htm#
#https://docs.sqlalchemy.org/en/14/orm/queryguide.html#select-statements

from config import logger, dbPath
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

try:
    engine = create_engine(dbPath, echo = False) #echo = True - вывод логов в консоль
    conn = engine.connect()
except Exception as err:
    logger.error('Не удается создать create_engine по dbPath = %s с ошибкой %s', dbPath, str(err))
meta = MetaData()


userPreferences = Table(
    'user_preferences', meta,
    Column('telegram_id', Integer, unique=True, index=True),
    Column('city', String, index=True),
    Column('exclude_bar', String),
    Column('exclude_theme', String),
    Column('exclude_org', String),
)

#функция для создания таблицы
def create_table():
    try:
        meta.create_all(engine)
    except Exception as err:
        logger.error('Не удается создать таблицу user_preferences с ошибкой %s', str(err))

#Запрос предпочтений пользователя, возвращает результат в формате (123456, 'Новосибирск', 'ART pub', '18+', 'mama quiz') либо None
def get_user_preferences(telegram_id):
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

def insert_new_user(telegram_id, city, excl_bar, excl_theme, excl_org):
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

def update_user_preferences(telegram_id, city, excl_bar, excl_theme, excl_org):
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
def delete_user(telegram_id):
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