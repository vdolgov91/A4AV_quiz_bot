import pytest
import dbOperations

@pytest.fixture(scope='session')
def temp_db_path(tmp_path_factory):
    '''Создать единую для всех тестов dbOperations папку в которой создастся файл БД ./app_db/a4av.db'''
    tmp_dir = tmp_path_factory.mktemp('tmp')
    return tmp_dir

