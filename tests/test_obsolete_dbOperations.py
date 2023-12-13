'''Тест кейсы для модуля dbOperations.py до рефакторинга. Запускать надо весь модуль целиком
Поодиночке часть кейсов работать не будут, так как тестовая БД не будет создана/ наполнена'''

import dbOperations
from config import dbPath

import os
import pytest

# Тестовые параметры пользователя
telegramId = 1234567890
city = 'Тестовый город'
city_update = 'Апдейтнутый город'
excl_bar = 'Тестовый бар'
excl_theme = 'Тестовая тема'
excl_org = 'Тестовый организатор'
wrong_param = ['wrong', 'param']


def test_create_db_with_wrong_path(monkeypatch, temp_db_path):
    '''Проверяет создание БД SQLite функцией create_database(): DBPath некорректен'''
    wrong_dbPath = 'qlite:///app_db/a4av.db'
    monkeypatch.chdir(temp_db_path)
    with pytest.raises(Exception):
        dbOperations.create_connection(wrong_dbPath)


def test_create_new_sqlite_db(monkeypatch, temp_db_path):
    '''Проверяет создание БД SQLite функцией create_database(): DBPath корректен, по этому адресу не существует БД.
    Здесь создаются объекты testEngine и testConn используемые в последующих функциях'''
    global testEngine, testConn
    monkeypatch.chdir(temp_db_path)
    testEngine, testConn = dbOperations.create_connection()
    expected_DB_file_path = temp_db_path / dbPath[10:]
    assert os.path.exists(expected_DB_file_path)


def test_create_new_table_in_sqlite_db(monkeypatch, temp_db_path):
    '''Проверяет создание новой таблицы в рамках тестового connection'''
    monkeypatch.chdir(temp_db_path)
    dbOperations.create_table(testEngine)
    path_to_DB_file = temp_db_path / dbPath[10:]  # вырезаем из dbPath 'sqlite:///'
    assert os.path.exists(path_to_DB_file) and os.path.getsize(path_to_DB_file) > 0


def test_insert_new_user():
    '''Проверяет добавление нового пользователя с уникальным telegramId'''
    insertUser = dbOperations.insert_new_user(testConn, telegramId, city, excl_bar, excl_theme, excl_org)
    assert insertUser


def test_insert_existing_user():
    '''Проверяет добавление нового пользователя с неуникальным telegramId'''
    insertUser = dbOperations.insert_new_user(testConn, telegramId, 'Москва', excl_bar, excl_theme, excl_org)
    assert not insertUser


def test_insert_new_incorrect_user():
    '''Проверяет добавление нового пользователя с уникальным telegramId, но некорректным типом данных'''
    insertUser = dbOperations.insert_new_user(testConn, wrong_param, city, excl_bar, excl_theme, excl_org)
    assert not insertUser


def test_get_user_preferences():
    '''Проверяет правильность извлеченных параметров пользователя'''
    expected = (telegramId, city, excl_bar, excl_theme, excl_org)
    userPreferences = dbOperations.get_user_preferences(testConn, telegramId)
    assert userPreferences == expected


def test_get_nonexistent_user_preferences():
    '''Проверяет правильность извлеченных параметров несуществующего пользователя'''
    userPreferences = dbOperations.get_user_preferences(testConn, telegramId + 100)
    assert userPreferences is None


def test_update_user_preferences():
    '''Проверяет обновление параметров пользователя'''
    updatedUserPreferences = dbOperations.update_user_preferences(testConn, telegramId, city_update, excl_bar, excl_theme, excl_org)
    assert updatedUserPreferences


def test_update_user_with_incorrect_preferences():
    '''Проверяет обновление параметров существующего пользователя при некорректных параметрах'''
    updatedUserPreferences = dbOperations.update_user_preferences(testConn, telegramId, wrong_param, excl_bar, excl_theme, excl_org)
    assert not updatedUserPreferences


def test_delete_user_with_wrongId():
    '''Проверяет удаление несуществующего пользователя'''
    deleteUser = dbOperations.delete_user(testConn, wrong_param)
    assert not deleteUser


def test_delete_user():
    '''Проверяет удаление существующего пользователя'''
    deleteUser = dbOperations.delete_user(testConn, telegramId)
    if deleteUser:
        userPreferences = dbOperations.get_user_preferences(testConn, telegramId)
        assert userPreferences is None
